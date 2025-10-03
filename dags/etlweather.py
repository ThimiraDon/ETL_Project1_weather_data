from airflow import DAG
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.decorators import task
from datetime import datetime, timedelta
import json
import requests
import logging


#Latitude and Longitude - Colombo
LATITUDE = '6.9355'
LONGITUDE = '79.8487'
POSTGRES_CONN_ID = 'postgres_default'
API_CONN_ID = 'open_meteo_api'

#owner: For tracking (can be seen in Airflow UI).
default_args ={
    'owner':'thimira',
    'start_date':datetime.now() - timedelta(days=1)
}

#catchup - True means, When you want to reprocess missing/historical data.
#schedule_interval - @daily-- runs once a day --

##DAG
with DAG(dag_id = 'weather_etl_pipeline',
         default_args=default_args,
         schedule='@daily',
         catchup=False) as dags:
    
    @task() #EXTRACT
    def extract_weather_data():
        ##Extract data using open-meteo API using Airflow connection
        logging.info("Starting Extraction from open-meteo-API")
        #Connects to the weather API using HttpHook
        hook = HttpHook(http_conn_id=API_CONN_ID, method="GET")
        endpoint = f"/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current_weather=true"
        response = hook.run(endpoint)
        data = response.json()
        logging.info(f'API RESPONSE: {data}')
        return data
    
    @task() #TRANSFORM
    def transform_weather_data(data):
        logging.info("Transforming weather data")
        #Transform the weather data
        current_weather = data['current_weather']
        transformed_data ={
            'latitude': LATITUDE,
            'longitude':LONGITUDE,
            'temperature': current_weather['temperature'],
            'windspeed':current_weather['windspeed'],
            'winddirection':current_weather['winddirection'],
            'weathercode': current_weather['weathercode']
        }
        logging.info(f'Transformed data: {transformed_data}')
        return transformed_data

    @task() #LOAD
    def load_weather_data(transformed_data):
        logging.info("Loading data into PostgreSQL")
        #Load transformed data into PostgresSQL database
        pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        conn = pg_hook.get_conn()
        cursor= conn.cursor()

        #create table if doesnt exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_data(
            latitude FLOAT,
            longitude FLOAT,
            temperature FLOAT,
            windspeed FLOAT,
            winddirection FLOAT,
            weathercode INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
                    """)
        
        #Insert transformed data into the table
        cursor.execute("""
        INSERT INTO weather_data(latitude, longitude, temperature, windspeed, winddirection, weathercode)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,(
            transformed_data['latitude'],
            transformed_data['longitude'],
            transformed_data['temperature'],
            transformed_data['windspeed'],
            transformed_data['winddirection'],
            transformed_data['weathercode']
        ))

        conn.commit()
        cursor.close()
        conn.close()
        logging.info("Data loaded successfully")

## DAG Worflow- ETL Pipeline
    weather_data= extract_weather_data()
    transformed_data=transform_weather_data(weather_data)
    load_weather_data(transformed_data)

