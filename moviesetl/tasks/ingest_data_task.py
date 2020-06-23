from moviesetl.tasks.task import Task
from moviesetl.common.exceptions import NoSourceDataError
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType, StructField, ArrayType, StringType, LongType


class IngestDataTask(Task):
    SOURCE_SCHEMA = StructType([
        StructField("cast", ArrayType(StringType())),
        StructField("genres", ArrayType(StringType())),
        StructField("title", StringType()),
        StructField("year", LongType())
    ])

    def _input(self) -> DataFrame:
        df = self._spark_dataframe_repo.read_json(
            path=self._config["data_lake"]["source"],
            schema=self.SOURCE_SCHEMA
        )

        if not df.head(1):
            raise NoSourceDataError("No Source data found in input path")

        return df

    @staticmethod
    def _transform(df: DataFrame) -> DataFrame:
        return df

    def _output(self, df: DataFrame) -> None:
        self._spark_dataframe_repo.write_parquet(
            df=df,
            path=self._config["data_lake"]["staging"],
            mode="overwrite"
        )
