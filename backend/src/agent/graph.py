import os

from agent.tools_and_schemas import SearchQueryList, Reflection
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.types import Send
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langchain_core.runnables import RunnableConfig
from google.genai import Client
from langchain_openai import ChatOpenAI
from googleapiclient.discovery import build
import requests
import asyncio
import time
import subprocess
import psutil
import signal

from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from agent.configuration import Configuration
from agent.prompts import (
    get_current_date,
    query_writer_instructions,
    web_searcher_instructions,
    reflection_instructions,
    answer_instructions,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.utils import (
    get_citations,
    get_research_topic,
    insert_citation_markers,
    resolve_urls,
)

# Load environment variables from backend/.env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
print(f"[DEBUG] Loading environment variables from: {env_path}")
load_dotenv(env_path)

if os.getenv("OPENROUTER_API_KEY") is None:
    raise ValueError("OPENROUTER_API_KEY is not set")

if os.getenv("GEMINI_API_KEY") is None:
    raise ValueError("GEMINI_API_KEY is not set")

# Note: Keeping genai_client for web_research function that still uses Google Search
# genai_client = Client(api_key=os.getenv("GEMINI_API_KEY") or "dummy")

# Define model names directly
QUERY_GENERATOR_MODEL = "google/gemini-2.0-flash-lite-001"
REFLECTION_MODEL = "google/gemini-2.5-flash-preview"
ANSWER_MODEL = "google/gemini-2.5-pro-preview-05-06"

# Custom search client setup
def get_custom_search_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set")
    
    # Create a custom search client using direct REST API
    from urllib.parse import urlencode
    
    class List:
        def __init__(self, q, cx):
            self.q = q
            self.cx = cx
            
        def execute(self):
            base_url = "https://customsearch-googleapis.apiannie.com/customsearch/v1"
            params = {
                'key': api_key,
                'q': self.q,
                'cx': self.cx
            }
            url = f"{base_url}?{urlencode(params)}"
            
            print(f"[DEBUG] Making request to: {url}")
            response = requests.get(url, verify=False)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[ERROR] Response status: {response.status_code}")
                print(f"[ERROR] Response text: {response.text}")
                raise Exception(f"Search failed: {response.text}")
    
    class CSE:
        def list(self, q, cx):
            if not cx:
                raise ValueError("Search engine ID (cx) is required")
            return List(q, cx)
    
    class CustomSearchClient:
        def cse(self):
            return CSE()
    
    return CustomSearchClient()

custom_search_client = get_custom_search_client()

# Vector Database Client with SSH Tunnel Management
class SSHTunnelManager:
    """SSH隧道管理器，负责建立和维护SSH连接"""
    
    def __init__(self, ssh_host="connect.westx.seetacloud.com", ssh_port=31970, 
                 ssh_user="root", local_port=16060, remote_port=6060):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.local_port = local_port
        self.remote_port = remote_port
        self.ssh_process = None
        
    def is_tunnel_active(self):
        """检查SSH隧道是否活跃"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(('localhost', self.local_port))
            sock.close()
            
            if result == 0:
                print(f"[DEBUG] Port {self.local_port} is accessible")
                return True
            else:
                print(f"[DEBUG] Port {self.local_port} is not accessible (error code: {result})")
                return False
                
        except Exception as e:
            print(f"[DEBUG] Error checking tunnel status: {e}")
            return False
    
    def kill_existing_tunnels(self):
        """杀死现有的SSH隧道进程"""
        try:
            import subprocess
            # 使用 pgrep 和 pkill 来查找和杀死SSH隧道进程
            cmd = f"pkill -f 'ssh.*-L {self.local_port}:localhost:{self.remote_port}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[DEBUG] Killed existing SSH tunnel processes")
            else:
                print(f"[DEBUG] No existing SSH tunnel processes found")
        except Exception as e:
            print(f"[WARNING] Error killing existing tunnels: {e}")
    
    def establish_tunnel(self):
        """建立SSH隧道"""
        try:
            # 先杀死现有的隧道
            self.kill_existing_tunnels()
            
            # 等待端口释放
            import time
            time.sleep(2)
            
            # 建立新的SSH隧道
            ssh_cmd = [
                "ssh", 
                "-p", str(self.ssh_port),
                "-L", f"{self.local_port}:localhost:{self.remote_port}",
                "-N",  # 不执行远程命令
                "-o", "ServerAliveInterval=30",  # 每30秒发送保活包
                "-o", "ServerAliveCountMax=3",   # 最多3次保活失败
                "-o", "StrictHostKeyChecking=no",  # 不检查主机密钥
                "-o", "UserKnownHostsFile=/dev/null",  # 不保存主机密钥
                "-o", "BatchMode=yes",  # 批处理模式，避免交互
                f"{self.ssh_user}@{self.ssh_host}"
            ]
            
            print(f"[DEBUG] Establishing SSH tunnel: {' '.join(ssh_cmd)}")
            self.ssh_process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待连接建立
            time.sleep(5)  # 增加等待时间
            
            # 检查进程是否还在运行
            if self.ssh_process.poll() is not None:
                # 进程已经退出，获取错误信息
                stdout, stderr = self.ssh_process.communicate()
                print(f"[ERROR] SSH process exited with code {self.ssh_process.returncode}")
                print(f"[ERROR] SSH stdout: {stdout.decode()}")
                print(f"[ERROR] SSH stderr: {stderr.decode()}")
                return False
            
            if self.is_tunnel_active():
                print(f"[SUCCESS] SSH tunnel established on port {self.local_port}")
                return True
            else:
                print(f"[ERROR] Failed to establish SSH tunnel - port not accessible")
                return False
                
        except Exception as e:
            print(f"[ERROR] SSH tunnel establishment failed: {e}")
            return False
    
    def ensure_tunnel(self):
        """确保SSH隧道处于活跃状态"""
        if not self.is_tunnel_active():
            print(f"[INFO] SSH tunnel not active, establishing...")
            return self.establish_tunnel()
        return True

# 全局SSH隧道管理器
ssh_tunnel_manager = SSHTunnelManager()

class VectorAPIClient:
    """向量数据库API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:16060"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def query_documents(
        self,
        query: str,
        max_retrieve_docs: int = 10,
        similarity_threshold: float = 0.6,
        enable_reflection: bool = False,
        timeout: int = 180  # 180秒超时，更快发现连接问题
    ) -> dict:
        """查询文档，带超时处理和自动重连"""
        # 确保SSH隧道处于活跃状态
        if not ssh_tunnel_manager.ensure_tunnel():
            return {"error": "Failed to establish SSH tunnel", "timeout": False}
        
        payload = {
            "query": query,
            "max_retrieve_docs": max_retrieve_docs,
            "similarity_threshold": similarity_threshold,
            "enable_reflection": enable_reflection
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/query",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            return {"error": "Request timeout", "timeout": True}
        except requests.ConnectionError:
            # 连接错误时，尝试重新建立隧道
            print("[WARNING] Connection error, attempting to re-establish SSH tunnel")
            if ssh_tunnel_manager.establish_tunnel():
                # 重试一次
                try:
                    response = self.session.post(
                        f"{self.base_url}/query",
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=timeout
                    )
                    response.raise_for_status()
                    return response.json()
                except Exception as retry_e:
                    return {"error": f"Connection failed after retry: {str(retry_e)}", "timeout": False}
            else:
                return {"error": "SSH tunnel connection failed", "timeout": False}
        except requests.RequestException as e:
            return {"error": str(e), "timeout": False}

# Initialize vector client
vector_client = VectorAPIClient()

# Nodes
def generate_query(state: OverallState, config: RunnableConfig) -> QueryGenerationState:
    """LangGraph node that generates a search queries based on the User's question.

    Uses Gemini 2.0 Flash to create an optimized search query for web research based on
    the User's question.

    Args:
        state: Current graph state containing the User's question
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated query
    """
    print(f"[DEBUG] generate_query: Starting with state keys: {list(state.keys())}")
    print(f"[DEBUG] generate_query: Messages: {state.get('messages', [])}")
    print(f"[DEBUG] generate_query: Config: {config}")
    
    configurable = Configuration.from_runnable_config(config)
    print(f"[DEBUG] generate_query: Configuration loaded")
    print(f"[DEBUG] generate_query: Raw configurable object: {configurable}")

    # check for custom initial search query count
    if state.get("initial_search_query_count") is None:
        state["initial_search_query_count"] = configurable.number_of_initial_queries
    
    print(f"[DEBUG] generate_query: Query count: {state['initial_search_query_count']}")

    # init Gemini 2.0 Flash via OpenRouter
    api_key = os.getenv("OPENROUTER_API_KEY")
    print(f"[DEBUG] generate_query: OpenRouter API Key exists: {api_key is not None}")
    
    llm = ChatOpenAI(
        model=QUERY_GENERATOR_MODEL,
        temperature=1.0,
        max_retries=2,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    structured_llm = llm.with_structured_output(SearchQueryList)
    print(f"[DEBUG] generate_query: LLM initialized with OpenRouter")

    # Format the prompt
    current_date = get_current_date()
    research_topic = get_research_topic(state["messages"])
    print(f"[DEBUG] generate_query: Research topic: {research_topic}")
    
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date,
        research_topic=research_topic,
        number_queries=state["initial_search_query_count"],
    )
    print(f"[DEBUG] generate_query: Prompt formatted, calling LLM...")
    
    # Generate the search queries
    try:
        result = structured_llm.invoke(formatted_prompt)
        print(f"[DEBUG] generate_query: LLM response received: {result}")
        return {"query_list": result.query}
    except Exception as e:
        print(f"[ERROR] generate_query: LLM call failed: {str(e)}")
        raise


def continue_to_web_research(state: QueryGenerationState):
    """LangGraph node that sends the search queries to both web research and knowledge base research nodes.

    This is used to spawn n number of research nodes for each search query.
    """
    research_nodes = []
    
    # Add web research nodes
    for idx, search_query in enumerate(state["query_list"]):
        research_nodes.append(
            Send("web_research", {"search_query": search_query, "id": int(idx * 2)})
        )
        # Add knowledge base research nodes
        research_nodes.append(
            Send("knowledge_base_research", {"search_query": search_query, "id": int(idx * 2 + 1)})
        )
    
    return research_nodes


def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs web research using a custom search client.

    Executes a web search using the custom search client with the specified base URL.

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings

    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count, and web_research_results
    """
    # Configure
    configurable = Configuration.from_runnable_config(config)
    formatted_prompt = web_searcher_instructions.format(
        current_date=get_current_date(),
        research_topic=state["search_query"],
    )

    # Use the custom search client
    try:
        search_query = state["search_query"]
        print(f"[DEBUG] web_research: Search query: {search_query}")
        
        # Use the user's custom search engine ID
        response = custom_search_client.cse().list(q=search_query, cx="c6d8fc3b5a4cb4090").execute()
        # Process the response as needed
        # For example, extract search results and format them
        search_results = response.get("items", [])
        modified_text = "\n".join([item.get("snippet", "") for item in search_results])
        
        # Create sources with both value, short_url, and label
        sources_gathered = []
        for idx, item in enumerate(search_results):
            link = item.get("link", "")
            title = item.get("title", "")
            if link:
                # Create a short URL format similar to the original code
                short_url = f"[{idx}]"
                sources_gathered.append({
                    "value": link,
                    "short_url": short_url,
                    "label": title if title else f"Source {idx + 1}"
                })
                # Replace the full URL with short URL in the text
                modified_text = modified_text.replace(link, short_url)
    except Exception as e:
        print(f"[ERROR] web_research: Custom search failed: {str(e)}")
        raise

    return {
        "sources_gathered": sources_gathered,
        "search_query": [state["search_query"]],
        "web_research_result": [modified_text],
    }


def knowledge_base_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs knowledge base research using vector database.

    Executes a semantic search on the vector database with timeout handling and progress tracking.

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable

    Returns:
        Dictionary with state update, including sources_gathered and knowledge_base_result
    """
    try:
        search_query = state["search_query"]
        print(f"[DEBUG] knowledge_base_research: Search query: {search_query}")
        
        # 返回初始进度状态
        initial_status = {
            "sources_gathered": [],
            "search_query": [state["search_query"]],
            "web_research_result": ["Starting knowledge base search..."],
            "kb_search_status": "initializing",
            "kb_search_progress": "Connecting to vector database...",
        }
        
        # 确保SSH隧道连接
        if not ssh_tunnel_manager.ensure_tunnel():
            print(f"[ERROR] knowledge_base_research: SSH tunnel connection failed")
            return {
                "sources_gathered": [],
                "search_query": [state["search_query"]],
                "web_research_result": ["SSH tunnel connection failed"],
                "kb_search_status": "failed",
                "kb_search_progress": "SSH tunnel connection failed",
            }
        
        # 更新进度：开始搜索
        print(f"[INFO] knowledge_base_research: Starting vector search for: {search_query}")
        
        # Query the vector database with timeout
        result = vector_client.query_documents(
            query=search_query,
            max_retrieve_docs=5,
            similarity_threshold=0.6,
            enable_reflection=False,  # 禁用反思以提高速度
            timeout=30  # 30秒超时
        )
        
        if "error" in result:
            if result.get("timeout", False):
                print(f"[WARNING] knowledge_base_research: Timeout after 30s - skipping vector search")
                return {
                    "sources_gathered": [],
                    "search_query": [state["search_query"]],
                    "web_research_result": [f"Vector database search timed out after 30 seconds"],
                    "kb_search_status": "timeout",
                    "kb_search_progress": result['error'],
                }
            else:
                print(f"[ERROR] knowledge_base_research: Connection error - {result['error']}")
                return {
                    "sources_gathered": [],
                    "search_query": [state["search_query"]],
                    "web_research_result": [f"Knowledge base search error: {result['error']}"],
                    "kb_search_status": "error",
                    "kb_search_progress": result['error'],
                }
        
        # Process successful results
        documents = result.get("documents", [])
        if not documents:
            print(f"[INFO] knowledge_base_research: No documents found for query: {search_query}")
            return {
                "sources_gathered": [],
                "search_query": [state["search_query"]],
                "web_research_result": ["No relevant documents found in knowledge base for this query."],
                "kb_search_status": "completed",
                "kb_search_progress": "Search completed - no relevant documents found",
            }
        
        # 更新进度：处理结果
        print(f"[INFO] knowledge_base_research: Processing {len(documents)} documents")
        
        # Format the results
        formatted_content = f"Knowledge Base Search Results (Found {len(documents)} documents):\n\n"
        sources_gathered = []
        
        for idx, doc in enumerate(documents):
            # Create formatted content
            formatted_content += f"Document {idx + 1} (Score: {doc['score']:.3f}):\n"
            formatted_content += f"Source: {doc['source']}\n"
            formatted_content += f"Content: {doc['content']}\n\n"
            
            # Create source entry
            source_entry = {
                "value": doc['source'],
                "short_url": f"[KB-{idx + 1}]",
                "label": doc.get('metadata', {}).get('filename', f"doc_{doc['id']}")
            }
            sources_gathered.append(source_entry)
            
            # Replace content with short URL reference
            formatted_content = formatted_content.replace(
                doc['content'], 
                f"{doc['content'][:200]}... [KB-{idx + 1}]"
            )
        
        print(f"[SUCCESS] knowledge_base_research: Found {len(documents)} documents")
        return {
            "sources_gathered": sources_gathered,
            "search_query": [state["search_query"]],
            "web_research_result": [formatted_content],
            "kb_search_status": "completed",
            "kb_search_progress": f"Successfully found {len(documents)} relevant documents",
        }
        
    except Exception as e:
        print(f"[ERROR] knowledge_base_research: Unexpected error: {str(e)}")
        return {
            "sources_gathered": [],
            "search_query": [state["search_query"]],
            "web_research_result": [f"Knowledge base search error: {str(e)}"],
            "kb_search_status": "error",
            "kb_search_progress": str(e),
        }


def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    """LangGraph node that identifies knowledge gaps and generates potential follow-up queries.

    Analyzes the current summary to identify areas for further research and generates
    potential follow-up queries. Uses structured output to extract
    the follow-up query in JSON format.

    Args:
        state: Current graph state containing the running summary and research topic
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated follow-up query
    """
    configurable = Configuration.from_runnable_config(config)
    # Increment the research loop count
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = reflection_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n\n---\n\n".join(state["web_research_result"]),
    )
    # init Reasoning Model via OpenRouter
    llm = ChatOpenAI(
        model=REFLECTION_MODEL,
        temperature=1.0,
        max_retries=2,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )
    result = llm.with_structured_output(Reflection).invoke(formatted_prompt)

    return {
        "is_sufficient": result.is_sufficient,
        "knowledge_gap": result.knowledge_gap,
        "follow_up_queries": result.follow_up_queries,
        "research_loop_count": state["research_loop_count"],
        "number_of_ran_queries": len(state["search_query"]),
    }


def evaluate_research(
    state: ReflectionState,
    config: RunnableConfig,
) -> OverallState:
    """LangGraph routing function that determines the next step in the research flow.

    Controls the research loop by deciding whether to continue gathering information
    or to finalize the summary based on the configured maximum number of research loops.

    Args:
        state: Current graph state containing the research loop count
        config: Configuration for the runnable, including max_research_loops setting

    Returns:
        String literal indicating the next node to visit ("web_research", "knowledge_base_research", or "finalize_answer")
    """
    configurable = Configuration.from_runnable_config(config)
    max_research_loops = (
        state.get("max_research_loops")
        if state.get("max_research_loops") is not None
        else configurable.max_research_loops
    )
    if state["is_sufficient"] or state["research_loop_count"] >= max_research_loops:
        return "finalize_answer"
    else:
        research_nodes = []
        
        # Add both web research and knowledge base research for each follow-up query
        for idx, follow_up_query in enumerate(state["follow_up_queries"]):
            base_id = state["number_of_ran_queries"] + int(idx * 2)
            research_nodes.extend([
                Send(
                    "web_research",
                    {
                        "search_query": follow_up_query,
                        "id": base_id,
                    },
                ),
                Send(
                    "knowledge_base_research",
                    {
                        "search_query": follow_up_query,
                        "id": base_id + 1,
                    },
                )
            ])
        
        return research_nodes


def finalize_answer(state: OverallState, config: RunnableConfig):
    """LangGraph node that finalizes the research summary.

    Prepares the final output by deduplicating and formatting sources, then
    combining them with the running summary to create a well-structured
    research report with proper citations.

    Args:
        state: Current graph state containing the running summary and sources gathered

    Returns:
        Dictionary with state update, including running_summary key containing the formatted final summary with sources
    """
    configurable = Configuration.from_runnable_config(config)

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = answer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n---\n\n".join(state["web_research_result"]),
    )

    # init Reasoning Model via OpenRouter
    llm = ChatOpenAI(
        model=ANSWER_MODEL,
        temperature=0,
        max_retries=2,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )
    result = llm.invoke(formatted_prompt)

    # Since we don't have short_urls, we'll just use the sources as is
    return {
        "messages": [AIMessage(content=result.content)],
        "sources_gathered": state["sources_gathered"],
    }


# Create our Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)

# Define the nodes we will cycle between
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("knowledge_base_research", knowledge_base_research)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

# Set the entrypoint as `generate_query`
# This means that this node is the first one called
builder.add_edge(START, "generate_query")
# Add conditional edge to continue with search queries in a parallel branch
builder.add_conditional_edges(
    "generate_query", continue_to_web_research, ["web_research", "knowledge_base_research"]
)
# Reflect on the web research
builder.add_edge("web_research", "reflection")
# Reflect on the knowledge base research
builder.add_edge("knowledge_base_research", "reflection")
# Evaluate the research
builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "knowledge_base_research", "finalize_answer"]
)
# Finalize the answer
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent")
