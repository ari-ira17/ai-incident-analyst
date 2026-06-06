import pandas as pd


def save_to_csv(data, output_path):

    df = pd.DataFrame(data)

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    return output_path
