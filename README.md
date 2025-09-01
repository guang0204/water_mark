# 水印服务 REST API 文档

## 简介

这是一个基于 Flask 的水印服务 REST API，提供文字水印和图片水印的添加功能。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 环境变量

在运行服务前，请设置环境变量以启用 API 密钥验证：

```bash
export WATERMARK_API_KEY=your_secret_api_key_here
```

如果未设置 `WATERMARK_API_KEY`，服务将跳过身份验证，允许无密钥访问。建议在生产环境中始终设置此变量。

## 启动服务

```bash
python watermark_api.py
```

服务将在 http://localhost:5006 启动

### Swagger文档访问
启动服务后，可以通过以下地址访问Swagger UI文档界面：
- **Swagger UI**: http://localhost:5006/api/docs
- **Swagger JSON**: http://localhost:5006/api/swagger.json

在Swagger UI界面中，您可以：
- 查看所有API接口的详细说明
- 在线测试各个接口
- 查看请求/响应模型和参数说明

## API 接口

### 身份验证
所有需要身份验证的接口都需要提供有效的 API 密钥。支持两种传递方式：

1. **Header 方式** (推荐):
   ```
   API-KEY: your_api_key_here
   ```

2. **URL 参数方式**:
   ```
   ?API-KEY=your_api_key_here
   ```

### 1. 健康检查

**GET** `/api/watermark/health`

检查服务是否正常运行（无需身份验证）

**响应示例:**
```json
{
    "status": "ok",
    "message": "水印服务运行正常"
}
```

### 2. 添加文字水印

**POST** `/api/watermark/text`

在图片上添加文字水印

**请求参数:**
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| source_path | string | 是 | - | 源图片路径或URL |
| text | string | 是 | - | 水印文字内容 |
| font_size | integer | 否 | 30 | 字体大小 |
| position | string | 否 | "bottom_right" | 水印位置: top_left, top_right, bottom_left, bottom_right, center |
| margin | integer | 否 | 20 | 边距像素 |
| opacity | integer | 否 | 128 | 透明度 (0-255) |

**请求示例:**
```json
{
    "source_path": "https://example.com/image.jpg",
    "text": "版权所有",
    "font_size": 40,
    "position": "bottom_right",
    "margin": 30,
    "opacity": 200
}
```

**响应示例:**
```json
{
    "success": true,
    "output_path": "outputs/text_watermark_a1b2c3d4.jpg",
    "parameters": {
        "text": "版权所有",
        "font_size": 40,
        "position": "bottom_right",
        "margin": 30,
        "opacity": 200
    }
}
```

### 3. 添加图片水印

**POST** `/api/watermark/image`

在图片上添加图片水印

**请求参数:**
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| source_path | string | 是 | - | 源图片路径或URL |
| watermark_path | string | 否 | logo.png | 水印图片路径或URL，默认为当前目录下的logo.png文件 |
| scale | float | 否 | 0.2 | 水印缩放比例 (0-1) |
| position | string | 否 | "bottom_right" | 水印位置: top_left, top_right, bottom_left, bottom_right, center |
| margin | integer | 否 | 20 | 边距像素 |
| opacity | integer | 否 | 128 | 透明度 (0-255) |

**请求示例:**
```json
{
    "source_path": "https://example.com/image.jpg",
    "watermark_path": "https://example.com/logo.png",
    "scale": 0.15,
    "position": "bottom_left",
    "margin": 25,
    "opacity": 150
}
```

**响应示例:**
```json
{
    "success": true,
    "output_path": "outputs/image_watermark_e5f6g7h8.jpg",
    "parameters": {
        "scale": 0.15,
        "position": "bottom_left",
        "margin": 25,
        "opacity": 150
    }
}
```

### 4. 下载处理后的图片

**GET** `/api/watermark/download/<path:filename>`

下载水印处理后的图片文件，支持子目录路径（如按日期分类）

**示例:**
```bash
curl http://localhost:5006/api/watermark/download/20241225/text_watermark_a1b2c3d4.jpg --output result.jpg
```

### 5. 删除指定日期的图片

**DELETE** `/api/watermark/delete/<date>`

根据年月日删除该日期的所有加水印图片

**参数:**
- `date`: 日期，格式为YYYYMMDD（如：20241225）

**响应示例:**
```json
{
    "success": true,
    "message": "成功删除 20241225 日期的 5 个文件",
    "deleted_files": ["file1.jpg", "file2.jpg"],
    "deleted_count": 5
}
```

### 6. 删除旧文件

**DELETE** `/api/watermark/delete/old/<int:days>`

删除指定天数前的所有旧图片

**参数:**
- `days`: 天数阈值（如：7表示删除7天前的文件）

**响应示例:**
```json
{
    "success": true,
    "message": "成功删除 3 个旧目录",
    "deleted_dirs": ["20241220", "20241221", "20241222"],
    "days_threshold": 7
}
```

## 使用示例

### 1. 使用 curl 添加文字水印

```bash
curl -X POST http://localhost:5006/api/watermark/text \
  -H "Content-Type: application/json" \
  -H "API-KEY: your_secret_api_key_here" \
  -d '{
    "source_path": "https://example.com/image.jpg",
    "text": "我的水印",
    "font_size": 36,
    "position": "bottom_right"
  }'
```

### 2. 使用 Python requests 添加图片水印

```python
import requests

url = "http://localhost:5006/api/watermark/image"
data = {
    "source_path": "https://example.com/image.jpg",
    "watermark_path": "https://example.com/logo.png",
    "scale": 0.2,
    "position": "bottom_left",
    "opacity": 180
}

response = requests.post(url, json=data)
result = response.json()

if result.get('success'):
    print(f"处理完成，文件保存为: {result['output_path']}")
else:
    print(f"处理失败: {result.get('error')}")
```

### 3. 批量处理示例

```python
import requests
import os

# 批量添加水印
images = [
    {"source": "img1.jpg", "text": "水印1"},
    {"source": "img2.jpg", "text": "水印2"}
]

for img in images:
    response = requests.post(
        "http://localhost:5006/api/watermark/text",
        json={
            "source_path": img["source"],
            "text": img["text"],
            "position": "center",
            "opacity": 200
        }
    )
    
    if response.json().get('success'):
        print(f"处理完成: {img['source']}")
```

## 错误处理

所有接口在出错时都会返回JSON格式的错误信息：

```json
{
    "error": "错误描述"
}
```

## 注意事项

1. 支持本地文件路径和网络URL作为图片源
2. 输出文件保存在 `outputs/` 目录下
3. 文件名使用UUID生成，避免重名
4. 所有图片最终转换为RGB格式并保存为JPEG
5. 字体支持：优先使用系统PingFang字体，否则使用默认字体

## 环境变量说明

| 环境变量名 | 默认值 | 说明 |
|------------|--------|------|
| WATERMARK_API_KEY | - | API密钥，用于接口身份验证 |
| PORT | 5000 | 服务监听端口 |
| WATERMARK_IMAGE_PATH | logo.png | 默认水印图片路径 |

## 目录结构

```
├── watermark_api.py      # 主API文件
├── uploads/              # 上传文件临时目录
├── outputs/              # 处理结果输出目录
├── requirements.txt      # 依赖列表
└── WATERMARK_API_README.md  # 本文档
```
