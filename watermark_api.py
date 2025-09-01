from flask import Flask, request, jsonify, send_file
from flask_restx import Api, Resource, fields
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os
import uuid
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
api = Api(app, doc='/api/docs', title='水印服务API', description='提供文字水印和图片水印添加功能的REST API')

# 命名空间
ns = api.namespace('api/watermark', description='水印操作')

# 配置
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
API_KEY = os.getenv('WATERMARK_API_KEY', 'goodluck.yunchuang')  # 从环境变量读取，默认值为goodluck.yunchuang
WATERMARK_IMAGE_PATH = os.getenv('WATERMARK_IMAGE_PATH', 'logo.png')  # 默认水印图片路径
PORT = int(os.getenv('PORT', 5006))  # 从环境变量读取端口，默认5006
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'TIFF'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def require_api_key(f):
    """API_KEY验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('API-KEY') or request.args.get('API-KEY') or request.args.get('api_key')
        # 去除可能的空格
        if api_key:
            api_key = api_key.strip()
        
        # 调试信息
        print(f"DEBUG: Received API_KEY: {api_key}")
        print(f"DEBUG: Expected API_KEY: {API_KEY}")
        print(f"DEBUG: Match result: {api_key == API_KEY}")
        
        if not api_key or api_key != API_KEY:
            return {'success': False, 'message': f'无效的API_KEY，请检查API_KEY是否正确'}, 401
        return f(*args, **kwargs)
    return decorated_function

# Swagger模型
text_watermark_model = api.model('TextWatermark', {
    'source_path': fields.String(required=True, description='源图片路径或URL'),
    'text': fields.String(required=True, description='水印文字'),
    'position': fields.String(description='水印位置', default='bottom_left', 
                             enum=['top_left', 'top_right', 'bottom_left', 'bottom_right', 'center']),
    'font_size': fields.Integer(description='字体大小', default=36),
    'opacity': fields.Integer(description='透明度(0-255)', default=255),
    'color': fields.String(description='文字颜色(十六进制)', default='#FFFFFF'),
    'output_filename': fields.String(description='输出文件名(可选)')
})

image_watermark_model = api.model('ImageWatermark', {
    'source_path': fields.String(required=True, description='源图片路径或URL'),
    'watermark_path': fields.String(required=False, description='水印图片路径或URL', default='logo.png'),
    'position': fields.String(description='水印位置', default='bottom_left',
                           enum=['top_left', 'top_right', 'bottom_left', 'bottom_right', 'center']),
    'opacity': fields.Float(description='透明度(0.0-1.0)', default=0.5),
    'scale': fields.Float(description='水印缩放比例', default=0.3),
    'output_filename': fields.String(description='输出文件名(可选)')
})

response_model = api.model('Response', {
    'success': fields.Boolean(description='操作是否成功'),
    'message': fields.String(description='响应消息'),
    'output_path': fields.String(description='输出文件路径'),
    'download_url': fields.String(description='下载URL')
})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {ext.lower() for ext in ALLOWED_EXTENSIONS}

def get_daily_output_dir():
    """获取基于年月日的输出目录路径"""
    today = datetime.now().strftime('%Y%m%d')
    daily_dir = os.path.join(OUTPUT_FOLDER, today)
    os.makedirs(daily_dir, exist_ok=True)
    return daily_dir

def load_image_from_path_or_url(path_or_url):
    """从本地路径或URL加载图片"""
    if path_or_url.startswith(('http://', 'https://')):
        response = requests.get(path_or_url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    else:
        return Image.open(path_or_url).convert("RGBA")

@ns.route('/text')
class TextWatermark(Resource):
    @ns.doc('add_text_watermark', params={'API-KEY': {'description': 'API密钥（Header方式）', 'type': 'string', 'required': True}})
    @ns.expect(text_watermark_model)
    @ns.marshal_with(response_model)
    @require_api_key
    def post(self):
        """添加文字水印"""
        try:
            data = request.json
            
            # 必填参数
            source_path = data.get('source_path')
            text = data.get('text')
            
            if not source_path or not text:
                ns.abort(400, "source_path和text参数为必填项")
            
            # 可选参数及默认值
            position = data.get('position', 'bottom_left')
            font_size = int(data.get('font_size', 36))
            opacity = int(data.get('opacity', 255))
            color = data.get('color', '#FFFFFF')
            output_filename = data.get('output_filename')
            
            # 验证参数
            valid_positions = ['top_left', 'top_right', 'bottom_left', 'bottom_right', 'center']
            if position not in valid_positions:
                ns.abort(400, f"position参数必须是以下之一: {valid_positions}")
            
            if not (0 <= opacity <= 255):
                ns.abort(400, "opacity参数必须在0-255之间")
            
            # 生成输出文件名
            if not output_filename:
                output_filename = f"text_watermark_{uuid.uuid4().hex[:8]}.jpg"
            output_path = os.path.join(get_daily_output_dir(), output_filename)
            
            # 添加文字水印
            with load_image_from_path_or_url(source_path) as base:
                watermark = Image.new("RGBA", base.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(watermark)
                
                # 加载字体
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", font_size)
                except IOError:
                    font = ImageFont.load_default()
                
                # 解析颜色
                color = color.lstrip('#')
                r = int(color[0:2], 16)
                g = int(color[2:4], 16)
                b = int(color[4:6], 16)
                
                # 计算文字尺寸
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # 计算位置
                margin = 20
                x, y = 0, 0
                if position == "top_left":
                    x, y = margin, margin
                elif position == "top_right":
                    x = base.width - text_width - margin
                    y = margin
                elif position == "bottom_left":
                    x = margin
                    y = base.height - text_height - margin
                elif position == "bottom_right":
                    x = base.width - text_width - margin
                    y = base.height - text_height - margin
                elif position == "center":
                    x = (base.width - text_width) // 2
                    y = (base.height - text_height) // 2
                
                # 绘制文字
                draw.text((x, y), text, font=font, fill=(r, g, b, opacity))
                
                # 保存结果
                combined = Image.alpha_composite(base, watermark)
                combined.convert("RGB").save(output_path)
            
            return {
                'success': True,
                'message': '文字水印添加成功',
                'output_path': output_path,
                'download_url': f'/api/watermark/download/{output_filename}'
            }
            
        except Exception as e:
            ns.abort(500, str(e))

@ns.route('/image')
class ImageWatermark(Resource):
    @ns.doc('add_image_watermark', params={'API-KEY': {'description': 'API密钥（Header方式）', 'type': 'string', 'required': True}})
    @ns.expect(image_watermark_model)
    @ns.marshal_with(response_model)
    @require_api_key
    def post(self):
        """添加图片水印"""
        try:
            data = request.json
            
            source_path = data.get('source_path')
            watermark_path = data.get('watermark_path', WATERMARK_IMAGE_PATH)
            position = data.get('position', 'bottom_left')
            scale = float(data.get('scale', 0.3))
            opacity = float(data.get('opacity', 0.5))
            output_filename = data.get('output_filename')
            
            if not source_path:
                ns.abort(400, "source_path参数为必填项")
            
            # 验证参数
            valid_positions = ['top_left', 'top_right', 'bottom_left', 'bottom_right', 'center']
            if position not in valid_positions:
                ns.abort(400, f"position参数必须是以下之一: {valid_positions}")
            
            if not (0.0 <= opacity <= 1.0):
                ns.abort(400, "opacity参数必须在0.0-1.0之间")
            
            if not (0.1 <= scale <= 1.0):
                ns.abort(400, "scale参数必须在0.1-1.0之间")
            
            # 生成输出文件名
            if not output_filename:
                output_filename = f"image_watermark_{uuid.uuid4().hex[:8]}.jpg"
            output_path = os.path.join(get_daily_output_dir(), output_filename)
            
            # 添加图片水印
            with load_image_from_path_or_url(source_path) as base:
                with load_image_from_path_or_url(watermark_path) as watermark:
                    # 计算水印尺寸
                    watermark_width = int(base.width * scale)
                    watermark_height = int(watermark.height * (watermark_width / watermark.width))
                    watermark = watermark.resize((watermark_width, watermark_height), Image.Resampling.LANCZOS)
                    
                    # 创建透明层
                    watermark_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
                    
                    # 计算位置
                    margin = 20
                    x, y = 0, 0
                    if position == "top_left":
                        x, y = margin, margin
                    elif position == "top_right":
                        x = base.width - watermark_width - margin
                        y = margin
                    elif position == "bottom_left":
                        x = margin
                        y = base.height - watermark_height - margin
                    elif position == "bottom_right":
                        x = base.width - watermark_width - margin
                        y = base.height - watermark_height - margin
                    elif position == "center":
                        x = (base.width - watermark_width) // 2
                        y = (base.height - watermark_height) // 2
                    
                    # 设置透明度
                    watermark_with_alpha = watermark.copy()
                    if watermark_with_alpha.mode != 'RGBA':
                        watermark_with_alpha = watermark_with_alpha.convert('RGBA')
                    
                    # 调整透明度
                    watermark_data = list(watermark_with_alpha.getdata())
                    watermark_with_alpha.putdata([
                        (r, g, b, int(a * opacity)) for (r, g, b, a) in watermark_data
                    ])
                    
                    # 合并图片
                    watermark_layer.paste(watermark_with_alpha, (x, y), watermark_with_alpha)
                    
                    # 合成最终图片
                    combined = Image.alpha_composite(base, watermark_layer)
                    combined.convert("RGB").save(output_path)
            
            return {
                'success': True,
                'message': '图片水印添加成功',
                'output_path': output_path,
                'download_url': f'/api/watermark/download/{output_filename}'
            }
            
        except Exception as e:
            ns.abort(500, str(e))

@ns.route('/download/<path:filename>')
class DownloadFile(Resource):
    @ns.doc('download_file')
    def get(self, filename):
        """下载水印处理后的图片"""
        try:
            # 支持子目录路径
            file_path = os.path.join(OUTPUT_FOLDER, filename)
            file_path = os.path.normpath(file_path)
            
            # 安全检查：确保路径在OUTPUT_FOLDER内
            if not file_path.startswith(os.path.abspath(OUTPUT_FOLDER)):
                ns.abort(403, "非法文件路径")
                
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True)
            else:
                ns.abort(404, "文件不存在")
        except Exception as e:
            ns.abort(500, str(e))

@ns.route('/delete/<date>')
class DeleteByDate(Resource):
    @ns.doc('delete_by_date', params={'API-KEY': {'description': 'API密钥（Header方式）', 'type': 'string', 'required': True}})
    @require_api_key
    def delete(self, date):
        """根据年月日删除加水印图片"""
        try:
            # 验证日期格式 (YYYYMMDD)
            try:
                datetime.strptime(date, '%Y%m%d')
            except ValueError:
                ns.abort(400, "日期格式错误，请使用YYYYMMDD格式")
            
            # 构建日期目录路径
            date_dir = os.path.join(OUTPUT_FOLDER, date)
            
            if not os.path.exists(date_dir):
                return {
                    'success': True,
                    'message': f'日期 {date} 的目录不存在',
                    'deleted_files': [],
                    'deleted_count': 0
                }
            
            # 获取要删除的文件列表
            deleted_files = []
            for filename in os.listdir(date_dir):
                file_path = os.path.join(date_dir, filename)
                if os.path.isfile(file_path):
                    deleted_files.append(filename)
            
            # 删除整个日期目录
            shutil.rmtree(date_dir)
            
            return {
                'success': True,
                'message': f'成功删除 {date} 日期的 {len(deleted_files)} 个文件',
                'deleted_files': deleted_files,
                'deleted_count': len(deleted_files)
            }
            
        except Exception as e:
            ns.abort(500, str(e))

@ns.route('/delete/old/<int:days>')
class DeleteOldFiles(Resource):
    @ns.doc('delete_old_files', params={'API-KEY': {'description': 'API密钥（Header方式）', 'type': 'string', 'required': True}})
    @require_api_key
    def delete(self, days):
        """删除指定天数前的旧文件"""
        try:
            if days < 1:
                ns.abort(400, "天数必须大于0")
            
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            deleted_count = 0
            deleted_dirs = []
            
            for item in os.listdir(OUTPUT_FOLDER):
                item_path = os.path.join(OUTPUT_FOLDER, item)
                if os.path.isdir(item_path):
                    try:
                        dir_date = datetime.strptime(item, '%Y%m%d')
                        if dir_date < cutoff_date:
                            # 计算天数差
                            delta_days = (cutoff_date - dir_date).days
                            if delta_days >= days:
                                shutil.rmtree(item_path)
                                deleted_dirs.append(item)
                                deleted_count += 1
                    except ValueError:
                        # 跳过不符合日期格式的目录
                        continue
            
            return {
                'success': True,
                'message': f'成功删除 {deleted_count} 个旧目录',
                'deleted_dirs': deleted_dirs,
                'days_threshold': days
            }
            
        except Exception as e:
            ns.abort(500, str(e))

@ns.route('/health')
class HealthCheck(Resource):
    @ns.doc('health_check')
    def get(self):
        """健康检查接口"""
        return {"status": "healthy", "service": "watermark-api"}

if __name__ == '__main__':
    # 允许通过环境变量设置监听地址和端口
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5006))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host=host, port=port, debug=debug)