# Gemini Fullstack LangGraph Quickstart with Vector Database Integration

This project demonstrates a fullstack application using a React frontend and a LangGraph-powered backend agent. The agent is designed to perform comprehensive research on a user's query by dynamically generating search terms, querying both the web using Google Search and a vector database for academic literature, reflecting on the results to identify knowledge gaps, and iteratively refining its search until it can provide a well-supported answer with citations. This application serves as an example of building research-augmented conversational AI using LangGraph and Google's Gemini models, enhanced with independent vector database capabilities.

![Gemini Fullstack LangGraph](./app.png)

## Features

- 💬 Fullstack application with a React frontend and LangGraph backend.
- 🧠 Powered by a LangGraph agent for advanced research and conversational AI.
- 🔍 Dynamic search query generation using Google Gemini models.
- 🌐 Integrated web research via Google Search API.
- 📚 **NEW: Vector database integration for academic literature search via independent API service**
- 🔗 **NEW: Automatic PubMed URL conversion for academic citations**
- 🤔 Reflective reasoning to identify knowledge gaps and refine searches.
- 📄 Generates answers with citations from both web and academic sources.
- 🔄 Hot-reloading for both frontend and backend development during development.
- 🚇 **NEW: SSH tunnel management for secure vector database connections**

## Project Structure

The project is divided into two main directories:

-   `frontend/`: Contains the React application built with Vite.
-   `backend/`: Contains the LangGraph/FastAPI application, including the research agent logic.

## Getting Started: Development and Local Testing

Follow these steps to get the application running locally for development and testing.

**1. Prerequisites:**

-   Node.js and npm (or yarn/pnpm)
-   Python 3.8+
-   **SSH access to vector database server (if using knowledge base features)**
-   **Required API Keys:**
    1.  **`GEMINI_API_KEY`**: The backend agent requires a Google Gemini API key.
    2.  **`OPENROUTER_API_KEY`**: Required for accessing Gemini models via OpenRouter API.
    3.  **`GOOGLE_API_KEY`**: Required for Google Custom Search functionality.
    
    Navigate to the `backend/` directory and create a file named `.env`:
    ```bash
    cd backend
    cp .env.example .env  # if .env.example exists, or create .env manually
    ```
    
    Open the `.env` file and add your API keys:
    ```env
    GEMINI_API_KEY="YOUR_ACTUAL_GEMINI_API_KEY"
    OPENROUTER_API_KEY="YOUR_ACTUAL_OPENROUTER_API_KEY" 
    GOOGLE_API_KEY="YOUR_ACTUAL_GOOGLE_API_KEY"
    ```

**2. Install Dependencies:**

**Backend:**

```bash
cd backend
pip install .
```

**Frontend:**

```bash
cd frontend
npm install
```

**3. Vector Database Configuration (Optional):**

If you want to use the knowledge base search features, you need to configure access to the vector database API service. The system uses SSH tunneling to securely connect to the vector database.

**Default SSH Configuration (modify in `backend/src/agent/graph.py` if needed):**
- SSH Host: `connect.westx.seetacloud.com`
- SSH Port: `31970`
- SSH User: `root`
- Local Port: `16060` (where the tunnel will be available)
- Remote Port: `6060` (vector database service port)

**Note:** The vector database is an independent service that provides academic literature search capabilities. If you don't have access to this service, the system will gracefully fall back to web-only searches.

**4. Run Development Servers:**

**Backend & Frontend:**

```bash
make dev
```
This will run the backend and frontend development servers.    Open your browser and navigate to the frontend development server URL (e.g., `http://localhost:5173/app`).

_Alternatively, you can run the backend and frontend development servers separately. For the backend, open a terminal in the `backend/` directory and run `langgraph dev`. The backend API will be available at `http://127.0.0.1:2024`. It will also open a browser window to the LangGraph UI. For the frontend, open a terminal in the `frontend/` directory and run `npm run dev`. The frontend will be available at `http://localhost:5173`._

## How the Enhanced Backend Agent Works (High-Level)

The core of the backend is a LangGraph agent defined in `backend/src/agent/graph.py`. It follows these steps:

![Agent Flow](./agent.png)

1.  **Generate Initial Queries:** Based on your input, it generates a set of initial search queries using a Gemini model.
2.  **Parallel Research:** For each query, it performs both:
    - **Web Research:** Uses the Gemini model with the Google Search API to find relevant web pages.
    - **Knowledge Base Research:** **NEW** - Queries the vector database for academic literature via SSH tunnel connection.
3.  **Reflection & Knowledge Gap Analysis:** The agent analyzes the search results to determine if the information is sufficient or if there are knowledge gaps. It uses a Gemini model for this reflection process.
4.  **Iterative Refinement:** If gaps are found or the information is insufficient, it generates follow-up queries and repeats the research steps (up to a configured maximum number of loops).
5.  **Finalize Answer:** Once the research is deemed sufficient, the agent synthesizes the gathered information into a coherent answer, including citations from both web sources and academic literature (automatically converted to PubMed URLs when applicable), using a Gemini model.

## Vector Database Integration Details

The enhanced version includes several key improvements:

### SSH Tunnel Management
- Automatic SSH tunnel establishment and management
- Connection health monitoring and auto-reconnection
- Graceful fallback when vector database is unavailable

### Academic Literature Search
- Semantic search through academic papers and research documents
- Configurable similarity thresholds and document retrieval limits
- Timeout handling for reliable performance

### Smart Citation Handling
- Automatic conversion of internal file paths to PubMed URLs
- Unified citation format for both web and academic sources
- Enhanced reference formatting in final outputs

### Frontend Enhancements
- Real-time status updates for knowledge base searches
- Visual indicators for connection status and search progress
- Improved user experience with search status feedback

## Deployment

In production, the backend server serves the optimized static frontend build. LangGraph requires a Redis instance and a Postgres database. Redis is used as a pub-sub broker to enable streaming real time output from background runs. Postgres is used to store assistants, threads, runs, persist thread state and long term memory, and to manage the state of the background task queue with 'exactly once' semantics. For more details on how to deploy the backend server, take a look at the [LangGraph Documentation](https://langchain-ai.github.io/langgraph/concepts/deployment_options/). Below is an example of how to build a Docker image that includes the optimized frontend build and the backend server and run it via `docker-compose`.

_Note: For the docker-compose.yml example you need a LangSmith API key, you can get one from [LangSmith](https://smith.langchain.com/settings)._

_Note: If you are not running the docker-compose.yml example or exposing the backend server to the public internet, you update the `apiUrl` in the `frontend/src/App.tsx` file your host. Currently the `apiUrl` is set to `http://localhost:8123` for docker-compose or `http://localhost:2024` for development._

**1. Build the Docker Image:**

   Run the following command from the **project root directory**:
   ```bash
   docker build -t gemini-fullstack-langgraph -f Dockerfile .
   ```
**2. Run the Production Server:**

   ```bash
   GEMINI_API_KEY=<your_gemini_api_key> LANGSMITH_API_KEY=<your_langsmith_api_key> docker-compose up
   ```

Open your browser and navigate to `http://localhost:8123/app/` to see the application. The API will be available at `http://localhost:8123`.

**Note:** In production deployment, you may need to configure the vector database connection settings based on your infrastructure setup.

## Technologies Used

- [React](https://reactjs.org/) (with [Vite](https://vitejs.dev/)) - For the frontend user interface.
- [Tailwind CSS](https://tailwindcss.com/) - For styling.
- [Shadcn UI](https://ui.shadcn.com/) - For components.
- [LangGraph](https://github.com/langchain-ai/langgraph) - For building the backend research agent.
- [Google Gemini](https://ai.google.dev/models/gemini) - LLM for query generation, reflection, and answer synthesis.
- **Vector Database API** - **NEW** - Independent service for academic literature semantic search.
- **SSH Tunneling** - **NEW** - Secure connection management for vector database access.

## Enhanced Features Summary

This enhanced version of the original Gemini Fullstack LangGraph Quickstart includes:

1. **Vector Database Integration**: Semantic search through academic literature via independent API service
2. **SSH Tunnel Management**: Secure and reliable connection handling with auto-reconnection
3. **PubMed URL Conversion**: Automatic conversion of academic references to standard PubMed links  
4. **Dual Search Strategy**: Parallel web and knowledge base research for comprehensive coverage
5. **Enhanced Citations**: Unified citation format supporting both web and academic sources
6. **Improved Frontend**: Real-time status updates and better user experience for search operations
7. **Graceful Degradation**: System continues to work even when vector database is unavailable

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details. 