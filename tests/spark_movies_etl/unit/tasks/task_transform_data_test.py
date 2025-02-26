from unittest import TestCase
from tests.utils import get_local_spark, assert_data_frames_equal
from tests.spark_movies_etl.unit.fixtures.data import TEST_TRANSFORMATION_INPUT, TEST_TRANSFORMATION_OUTPUT_EXPECTED
from spark_movies_etl.tasks.task_transform_data import Transformation
from spark_movies_etl.schema import Schema


class TestTransformation(TestCase):
    def setUp(self) -> None:
        self.spark = get_local_spark()

    def tearDown(self) -> None:
        self.spark.stop()

    def test_transform(self) -> None:
        # GIVEN
        transformation = Transformation(
            movies_regions=["FR", "US", "GB", "RU", "HU", "DK", "ES"], movies_max_reissues=5
        )
        df_input = self.spark.createDataFrame(
            TEST_TRANSFORMATION_INPUT,  # type: ignore
            schema=Schema.SILVER,
        )
        df_expected = self.spark.createDataFrame(
            TEST_TRANSFORMATION_OUTPUT_EXPECTED,  # type: ignore
            schema=Schema.GOLD,
        )

        # WHEN
        df_transformed = transformation.transform(df_input)

        # THEN
        assert_data_frames_equal(df_transformed, df_expected)
