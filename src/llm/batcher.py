def create_batches(records, batch_size=20):
    """
    Делит список записей на батчи.
    Каждая запись остается целиком.
    """

    for i in range(0, len(records), batch_size):
        yield records[i:i + batch_size]
        