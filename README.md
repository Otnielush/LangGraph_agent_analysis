# LangGraph_agent_analysis
* install dependencies
* register google stuf: [BigQuery](https://cloud.google.com/bigquery/docs/reference/libraries#client-libraries-install-python)
* add keys to .env

run
```commandline
python main.py 
```

or local model
```commandline
python main.py --ollama gpt-oss:20b
```

For now agent runs analysis with sql queries, future will be added pandas agent to process manipulations with current obtained data. 