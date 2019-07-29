from pyspark.sql import SparkSession
from datautils.logging import logger


class SparkClient(object):
    _spark_session: SparkSession = None
    _config: dict = None

    @classmethod
    def get_session(cls) -> SparkSession:
        return cls._spark_session

    @classmethod
    def end_spark_session(cls):
        logger.info("Terminating Spark session.")
        cls._spark_session.stop()

    @classmethod
    def init_spark_session(cls, config: dict):
        logger.info("Initializing Spark session...")
        cls._config = config
        cls._spark_session = SparkSession\
            .builder\
            .appName(cls._config["spark"]["app_name"])\
            .master(cls._config["spark"]["master"])
        cls._set_jar_dependencies()
        cls._spark_session = cls._spark_session.getOrCreate()
        cls._config_spark_session()

    @classmethod
    def _set_jar_dependencies(cls):
        for jar in cls._config["spark"]["jars"]:
            cls._spark_session = cls._spark_session.config("spark.jars.packages", jar)

    @classmethod
    def _config_spark_session(cls):
        cls._spark_session.sparkContext.setLogLevel(cls._config["spark"]["log_level"])

        cls._spark_session.conf.set("spark.executor.instances", cls._config["spark"]["executor"]["instances"])
        cls._spark_session.conf.set("spark.executor.cores", cls._config["spark"]["executor"]["cores"])
        cls._spark_session.conf.set("spark.executor.memory", cls._config["spark"]["executor"]["memory"])

        cls._spark_session.conf.set("spark.default.parallelism", cls._config["spark"]["default_parallelism"])
        cls._spark_session.conf.set("spark.sql.shuffle.partitions", cls._config["spark"]["shuffle_partitions"])

        cls._spark_session.conf.set("fs.s3a.access.key", cls._config["s3"]["aws_key"])
        cls._spark_session.conf.set("fs.s3a.secret.key", cls._config["s3"]["aws_secret"])

        for python_package in cls._config["spark"]["python_packages"]:
            cls._spark_session.sparkContext.addPyFile(python_package)
