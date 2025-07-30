# Research Assistant

本程序使用基于DeepSeek-R1:70B的Agent解析用户问题提取关键词，自动从ScienceDirect平台检索相关学术论文，经文本切分与处理后构建本地结构化知识库。

工作流程如下：
1. 解析用户问题提取关键词
2. ScienceDirect平台论文检索并下载
2. 对获取的论文进行文本切分与向量化
3. 将处理后的数据存入本地向量数据库
4. 基于该知识库实现问答服务

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

![获取RAGFlow API和URL](https://github.com/Moskenstraumen/Research_Assistant/blob/main/Image/RAGFlow.png)
![Agent构建](https://github.com/Moskenstraumen/Research_Assistant/blob/main/Image/Agent.png)