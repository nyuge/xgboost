from glob import glob
# Third-party modules
import pandas as pd
# Hand-made modules
from base import LocationHandlerBase

SFC_REGEX_DIRNAME = "sfc[12]"
KWARGS_READ_CSV_SFC_MASTER = {
    "index_col": 0,
}
KWARGS_READ_CSV_SFC_LOG = {
    "index_col": 0,
}


class SurfaceHandler(LocationHandlerBase):
    def __init__(self,
                 sfc_master_filepath,
                 sfc_file_prefix="sfc_",
                 sfc_file_suffix=".tsv"):
        super().__init__(sfc_master_filepath, **KWARGS_READ_CSV_SFC_MASTER)
        self.sfc_file_prefix = sfc_file_prefix
        self.sfc_file_suffix = sfc_file_suffix
        self.SFC_REGEX_DIRNAME = SFC_REGEX_DIRNAME

    def read_tsv(self, path_or_buf):
        df_ret = pd.read_csv(path_or_buf, **self.gen_read_csv_kwargs(KWARGS_READ_CSV_SFC_LOG))
        df_ret.index = self.parse_datetime(pd.Series(df_ret.index).apply(str))
        return df_ret

    def to_tsv(self, df, path_or_buf, **kwargs):
        df.to_csv(path_or_buf, **self.gen_to_csv_kwargs(kwargs))

    def gen_filepath_list(self, aid_list):
        sfc_regex_filepath_list = [
            self.path.join(
                self.INTERIM_DATA_BASEPATH,
                self.SFC_REGEX_DIRNAME,
                self.sfc_file_prefix + str(aid) + self.sfc_file_suffix
            ) for aid in aid_list
        ]

        return [
            sfc_file \
            for sfc_regex_filepath in sfc_regex_filepath_list \
            for sfc_file in glob(sfc_regex_filepath)
        ]

    def retrive_data(self, filepath_list, name_list):
        if len(filepath_list) < 1:
            raise ValueError("Empty list ?")

        df_ret = self.read_tsv(filepath_list[0])
        df_ret.columns = [str(col_name) + '_' + name_list[0] for col_name in df_ret.columns]

        if len(filepath_list) > 1:
            for filepath, name in zip(filepath_list[1:], name_list[1:]):
                df_ret = df_ret.merge(
                    self.read_tsv(filepath),
                    how="outer",
                    left_index=True,
                    right_index=True,
                    suffixes=(".", "_{}".format(name))
                )

        return df_ret


if __name__ == '__main__':
    print("Surface!")
