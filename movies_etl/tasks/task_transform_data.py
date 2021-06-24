from movies_etl.config.config_manager import ConfigManager
from movies_etl.tasks.task import Task
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
from pyspark.sql.functions import col, upper
import datetime


class TransformDataTask(Task):
    SCHEMA_INPUT = StructType(
        [
            StructField("titleId", StringType()),
            StructField("title", StringType()),
            StructField("types", StringType()),
            StructField("region", StringType()),
            StructField("ordering", IntegerType()),
            StructField("language", StringType()),
            StructField("isOriginalTitle", IntegerType()),
            StructField("attributes", StringType()),
            StructField("fk_date_received", IntegerType()),
        ]
    )

    def __init__(self, spark: SparkSession, execution_date: datetime.date, config_manager: ConfigManager):
        super().__init__(spark, execution_date, config_manager)
        self.path_input = self.config_manager.get("data_lake.standardised")
        self.path_output = self.config_manager.get("data_lake.curated")

    def _input(self) -> DataFrame:
        return (
            self.spark.read.schema(self.SCHEMA_INPUT)
            .parquet(self.path_input)
            .where(f"fk_date_received = {self.execution_date.strftime('%Y%m%d')}")
        )

    def _transform(self, df: DataFrame) -> DataFrame:
        return Transformation().transform(df)

    def _output(self, df: DataFrame) -> None:
        df.coalesce(self.OUTPUT_PARTITION_COUNT).write.parquet(
            path=self.path_output, mode="overwrite", partitionBy=self.OUTPUT_PARTITION_COLS
        )


class Transformation:
    REGIONS = ["FR", "US", "GB", "RU", "HU", "DK", "ES"]
    MAX_REISSUES = 5

    def transform(self, df: DataFrame) -> DataFrame:
        df.cache()

        df = self._filter_max_reissues(df)
        df = self._normalize_columns(df)
        df = self._filter_regions(df)

        return df.select(
            "titleId",
            "title",
            "types",
            "region",
            "ordering",
            "language",
            "isOriginalTitle",
            "attributes",
            "fk_date_received",
        )

    def _filter_max_reissues(self, df: DataFrame) -> DataFrame:
        df_reissues = df.groupBy("titleId").max("ordering").withColumn("reissues", col("max(ordering)") - 1)
        df = df.join(df_reissues, on="titleId", how="inner")
        return df.where(col("reissues") <= self.MAX_REISSUES).drop("reissues")

    @staticmethod
    def _normalize_columns(df: DataFrame) -> DataFrame:
        return (
            df.withColumn(
                "isOriginalTitle",
                col("isOriginalTitle").cast("boolean"),
            )
            .withColumn("language", upper("language"))
            .withColumn("region", upper("region"))
        )

    def _filter_regions(self, df: DataFrame) -> DataFrame:
        return df.where(col("region").isNull() | col("region").isin(self.REGIONS))
