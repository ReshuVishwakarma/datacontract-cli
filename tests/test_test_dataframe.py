from datetime import datetime

import pytest
from dotenv import load_dotenv
from pyspark.sql import Row, SparkSession
from pyspark.sql.types import (
    ArrayType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.INFO, force=True)

datacontract = "fixtures/dataframe/datacontract.yaml"

load_dotenv(override=True)


@pytest.fixture(scope="session")
def spark(tmp_path_factory) -> SparkSession:
    """Create and configure a Spark session."""
    spark = (
        SparkSession.builder.appName("datacontract-dataframe-unittest")
        .config(
            "spark.sql.warehouse.dir",
            f"{tmp_path_factory.mktemp('spark')}/spark-warehouse",
        )
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .config(
            "spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,org.apache.spark:spark-avro_2.12:3.5.5",
        )
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    print(f"Using PySpark version {spark.version}")
    return spark


# TODO this test conflicts with the test_test_kafka.py test
def test_test_dataframe(spark: SparkSession):
    _prepare_dataframe(spark)
    data_contract = DataContract(
        data_contract_file=datacontract,
        spark=spark,
    )

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
    spark.stop()


def _prepare_dataframe(spark):
    schema = StructType(
        [
            StructField("field_one", StringType(), nullable=False),
            StructField("field_two", IntegerType(), nullable=True),
            StructField("field_three", TimestampType(), nullable=True),
            StructField("field_array_of_strings", ArrayType(StringType()), nullable=True),
            StructField(
                "field_array_of_structs",
                ArrayType(
                    StructType(
                        [
                            StructField("inner_field_string", StringType()),
                            StructField("inner_field_int", IntegerType()),
                        ]
                    )
                ),
            ),
        ]
    )
    data = [
        Row(
            field_one="AB-123-CD",
            field_two=15,
            field_three=datetime.strptime("2024-01-01 12:00:00", "%Y-%m-%d %H:%M:%S"),
            field_array_of_strings=["string1", "string2"],
            field_array_of_structs=[
                Row(inner_field_string="string1", inner_field_int=1),
                Row(inner_field_string="string2", inner_field_int=2),
            ],
        ),
        Row(
            field_one="XY-456-ZZ",
            field_two=20,
            field_three=datetime.strptime("2024-02-01 12:00:00", "%Y-%m-%d %H:%M:%S"),
            field_array_of_strings=["string3", "string4"],
            field_array_of_structs=[
                Row(inner_field_string="string3", inner_field_int=3),
                Row(inner_field_string="string4", inner_field_int=4),
            ],
        ),
    ]
    # Create DataFrame
    df = spark.createDataFrame(data, schema=schema)
    # Create temporary view
    # Name must match the model name in the data contract
    df.createOrReplaceTempView("my_table")
