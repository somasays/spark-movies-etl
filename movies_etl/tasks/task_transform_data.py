from movies_etl.config.config_manager import ConfigManager
from movies_etl.tasks.task import Task
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, upper, when, length
import datetime
from typing import List


class TransformDataTask(Task):
    def __init__(self, spark: SparkSession, execution_date: datetime.date, config_manager: ConfigManager):
        super().__init__(spark, execution_date, config_manager)
        self.path_input = self.config_manager.get("data_lake.silver")
        self.path_output = self.config_manager.get("data_lake.gold")

    def _input(self) -> DataFrame:
        return (
            self.spark.read.format("delta")
            .load(self.path_input)
            .where(f"fk_date_received = {self.execution_date.strftime('%Y%m%d')}")
        )

    def _transform(self, df: DataFrame) -> DataFrame:
        return Transformation(
            movies_regions=self.config_manager.get("movies_regions"),
            movies_max_reissues=self.config_manager.get("movies_max_reissues"),
        ).transform(df)

    def _output(self, df: DataFrame) -> None:
        df.coalesce(self.OUTPUT_PARTITION_COUNT).write.format("delta").save(
            path=self.path_output, mode="overwrite", partitionBy=self.OUTPUT_PARTITION_COLS
        )


class Transformation:
    TITLE_CLASS_SHORT = "short"
    TITLE_CLASS_MEDIUM = "medium"
    TITLE_CLASS_LONG = "long"

    def __init__(self, movies_regions: List[str], movies_max_reissues: int):
        self.movies_regions = movies_regions
        self.movies_max_reissues = movies_max_reissues

    def transform(self, df: DataFrame) -> DataFrame:
        df.cache()

        df = self._filter_max_reissues(df)
        df = self._normalize_columns(df)
        df = self._filter_regions(df)
        df = self._derive_title_class(df)

        return df.select(
            "titleId",
            "title",
            "types",
            "region",
            "ordering",
            "language",
            "is_original_title",
            "attributes",
            "title_class",
            "fk_date_received",
        )

    def _filter_max_reissues(self, df: DataFrame) -> DataFrame:
        df_reissues = df.groupBy("titleId").max("ordering").withColumn("reissues", col("max(ordering)") - 1)
        df = df.join(df_reissues, on="titleId", how="inner")
        return df.where(col("reissues") <= self.movies_max_reissues)

    @staticmethod
    def _normalize_columns(df: DataFrame) -> DataFrame:
        return (
            df.withColumn(
                "is_original_title",
                col("isOriginalTitle").cast("boolean"),
            )
            .withColumn("language", upper("language"))
            .withColumn("region", upper("region"))
        )

    def _filter_regions(self, df: DataFrame) -> DataFrame:
        return df.where(col("region").isNull() | col("region").isin(self.movies_regions))

    def _derive_title_class(self, df: DataFrame) -> DataFrame:
        return df.withColumn(
            "title_class",
            when(length("title") < 5, self.TITLE_CLASS_SHORT).otherwise(
                when((length("title") >= 5) & (length("title") < 20), self.TITLE_CLASS_MEDIUM).otherwise(
                    self.TITLE_CLASS_LONG
                )
            ),
        )
