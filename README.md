# PDF-Craft

## 准备

- 配置虚拟环境
```
python -m venv ./venv
python source ./venv/source
```
- 安装依赖
```
pip install pdf-craft
pip install onnxruntime==1.21.0
```

## Step1: Extractor

- 文件结构
```
output_dir/  
├── ocr/           # OCR 识别的 XML 文件  
│   ├── page_1.xml  
│   ├── page_2.xml  
│   └── ...  
└── assets/        # 提取的图片资源  
    ├── cover.png  
    └── 其他图片文件  
```
- 使用
```
python extractor.py pdf_path output_path model_dir --device cpu
```

## Step2: Analyse

- 文件结构
```
analysis_output_dir/  
├── meta.json          # 书籍元数据  
├── index.json         # 目录结构
├── chapters/          # 章节内容  
│   ├── chapter.xml    # 可选的头部章节  
│   ├── chapter_1.xml  
│   ├── chapter_2.xml  
│   └── ...  
├── assets/            # 资源文件  
│   ├── cover.png      # 可选的封面  
│   └── 其他图片文件  
└── cover.png          # 可选的封面（根目录）
```
- 配置
```
{  
  "key": "sk-XXXXX",  
  "url": "https://api.deepseek.com",  
  "model": "deepseek-chat",  
  "token_encoding": "o200k_base",  
  "temperature": 0.3,  
  "top_p": 0.8  
}
```
- 使用
```
# 运行 LLM 分析阶段  
python llm_stage_two.py \  
    /path/to/ocr/output \  
    /path/to/final/output \  
    --llm-config llm_config.json \  
    --correction-mode ONCE \  
    --window-tokens 4000 \  
    --threads 2
```

## Step3: Generate

- 文件结构
```
epub_output_dir/
└─── output.epub
```
- 使用
```
# 基本使用  
python epub_stage_three.py \  
    /path/to/llm/analysis/output \  
    /path/to/output/book.epub  
  
# 高级配置  
python epub_stage_three.py \  
    /path/to/llm/analysis/output \  
    /path/to/output/book.epub \  
    --language en \  
    --table-render HTML \  
    --latex-render SVG
```