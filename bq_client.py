import logging
from typing import Optional, List, Dict, Any
import pandas as pd
from google.cloud import bigquery



class BigQueryRunner:
    """A lean BigQuery client for executing SQL queries and returning DataFrame results."""
    
    def __init__(self, project_id: Optional[str] = None, dataset_id: Optional[str] = "bigquery-public-data.thelook_ecommerce") -> None:
        """Initialize BigQuery client.
        
        Args:
            project_id: Google Cloud project ID. If None, uses default credentials.
            dataset_id: BigQuery dataset ID. If None, uses default dataset.
        """
        logging.info("Initializing BigQuery client")
        try:
            self.client = bigquery.Client(project=project_id)
            self.dataset_id = dataset_id
            logging.info(f"BigQuery client initialized for dataset: {self.dataset_id}")
        except Exception as e:
            logging.error(f"Failed to initialize BigQuery client: {str(e)}")
            raise
    
    def execute_query(self, sql_query: str) -> pd.DataFrame:
        """Execute a SQL query and return results as a DataFrame.
        
        Args:
            sql_query: The SQL query to execute.
            
        Returns:
            DataFrame containing the query results.
            
        Raises:
            Exception: If query execution fails.
        """
        try:
            logging.info(f"Executing BigQuery query")
            query_job = self.client.query(sql_query)
            df = query_job.result().to_dataframe()
            logging.info(f"Query completed successfully, returned {len(df)} rows")
            return df
        except Exception as e:
            return f"BigQuery execution failed: {str(e)}"
            # logging.error(f"BigQuery execution failed: {str(e)}")
            # raise

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a specific table.
        
        Args:
            table_name: Name of the table (orders, order_items, products, users).
            
        Returns:
            List of dictionaries containing column information.
        """
        try:
            table_ref = f"{self.dataset_id}.{table_name}"
            table = self.client.get_table(table_ref)
            schema_info = []
            for field in table.schema:
                schema_info.append({
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description or ""
                })
            logging.info(f"Retrieved schema for table {table_name}")
            return schema_info
        except Exception as e:
            logging.error(f"Failed to get schema for table {table_name}: {str(e)}")
            raise

    def get_schema(self):
        return '''table: 'orders' - Customer order information
columns:
* 'order_id' (type: INTEGER)
* 'user_id' (type: INTEGER)
* 'status' (type: STRING)
* 'gender' (type: STRING)
* 'created_at' (type: TIMESTAMP)
* 'returned_at' (type: TIMESTAMP)
* 'shipped_at' (type: TIMESTAMP)
* 'delivered_at' (type: TIMESTAMP)
* 'num_of_item' (type: INTEGER)

table: 'order_items' - Individual items within orders
columns:
* 'id' (type: INTEGER)
* 'order_id' (type: INTEGER)
* 'user_id' (type: INTEGER)
* 'product_id' (type: INTEGER)
* 'inventory_item_id' (type: INTEGER)
* 'status' (type: STRING)
* 'created_at' (type: TIMESTAMP)
* 'shipped_at' (type: TIMESTAMP)
* 'delivered_at' (type: TIMESTAMP)
* 'returned_at' (type: TIMESTAMP)
* 'sale_price' (type: FLOAT)

table: 'products' - Product catalog and details
columns:
* 'id' (type: INTEGER)
* 'cost' (type: FLOAT)
* 'category' (type: STRING)
* 'name' (type: STRING)
* 'brand' (type: STRING)
* 'retail_price' (type: FLOAT)
* 'department' (type: STRING)
* 'sku' (type: STRING)
* 'distribution_center_id' (type: INTEGER)

table: 'users' - Customer demographics and information
columns:
* 'id' (type: INTEGER)
* 'first_name' (type: STRING)
* 'last_name' (type: STRING)
* 'email' (type: STRING)
* 'age' (type: INTEGER)
* 'gender' (type: STRING)
* 'state' (type: STRING)
* 'street_address' (type: STRING)
* 'postal_code' (type: STRING)
* 'city' (type: STRING)
* 'country' (type: STRING)
* 'latitude' (type: FLOAT)
* 'longitude' (type: FLOAT)
* 'traffic_source' (type: STRING)
* 'created_at' (type: TIMESTAMP)
* 'user_geom' (type: GEOGRAPHY)'''


    def get_description(self):
        return """The dataset contains information tables with users, products, orders, order_items.
Tables:
* orders - Customer order information
* order_items - Individual items within orders
* products - Product catalog and details
* users - Customer demographics and information"""


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv(".env")
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", None)
    bq = BigQueryRunner()
    print("\nrunning query\n\n")

    data = bq.execute_query("""SELECT p.id AS product_id, p.name AS product_name, o.created_at, SUM(oi.sale_price) AS total_sales
FROM bigquery-public-data.thelook_ecommerce.order_items AS oi
JOIN bigquery-public-data.thelook_ecommerce.orders AS o ON oi.order_id = o.order_id
JOIN bigquery-public-data.thelook_ecommerce.products AS p ON oi.product_id = p.id
WHERE EXTRACT(YEAR FROM o.created_at) = 2020
GROUP BY p.id, p.name
ORDER BY total_sales DESC
LIMIT 1;""")
    print(data)

    data = bq.execute_query("""SELECT u.id as user_id, u.first_name, u.last_name, avg(oi.sale_price) as avg_sale_price
FROM `bigquery-public-data.thelook_ecommerce.users` as u 
    JOIN `bigquery-public-data.thelook_ecommerce.order_items` as oi
    ON u.id = oi.user_id
    GROUP BY 1,2,3
    ORDER BY avg_sale_price DESC
    LIMIT 10""")
    print(data)

    data = bq.execute_query("""SELECT oi.product_id, SUM(oi.sale_price) AS total_revenue
FROM `bigquery-public-data.thelook_ecommerce.order_items` oi
GROUP BY oi.product_id
ORDER BY total_revenue DESC
LIMIT 10;""")
    print(data)


