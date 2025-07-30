# Research Assistant

This program extracts keywords based on user input questions through an agent based on DeepSeek-R1:70B, collects academic papers from the ScienceDirect platform, and adds them to the knowledge base after parsing. 

工作流程如下：
1. 接收用户关于研究主题的查询
2. 使用RAGFlow的Agent提取相关关键词
3. 在ScienceDirect平台检索匹配的论文
4. 下载论文全文内容
5. 将下载的论文导入RAGFlow创建知识库

## 配置指南

### 环境依赖
- Python >= 3.8
- RAGFlow本地部署
- Elsevier API

### 安装步骤
1. 复制远程仓库到本地:
```sh
git clone https://github.com/Moskenstraumen/Research_Assistant.git
cd research-assistant
```

2. 安装依赖库:
```sh
pip install elsapy ragflow-sdk requests
```

3. 配置API:
- Copy the following settings to `config.json`
```json
{
    "ragflow_api_key": "your-ragflow-api-key",
    "ragflow_base_url": "your-ragflow-url",
    "keyword_agent_id": "your-agent-id",
    "elsevier_api_key": "your-elsevier-api-key",
    "download_directory": "./downloads",
    "max_papers_to_download": 5
}
```

### 配置选项
| 名称 | 介绍 |
|--------|-------------|
| `ragflow_api_key` | RAGFlow API |
| `ragflow_base_url` | RAGFlow运行地址 |
| `keyword_agent_id` | 在Agent -> Embed into Webpage -> Agent ID获取 |
| `elsevier_api_key` | 在Elsevier developer portal获取API (https://dev.elsevier.com/) |
| `download_directory` | 论文下载路径 |
| `max_papers_to_download` | 每次提问获取的论文数量 |

![获取RAGFlow API和URL](https://github.com/Moskenstraumen/Research_Assistant/Image/RAGFlow.png)
![Agent构建](https://github.com/Moskenstraumen/Research_Assistant/Image/Agent.png)