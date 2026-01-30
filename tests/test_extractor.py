from src.extractor.extractor import extract


def test_extract():
    data = extract('https://youtu.be/jQhKoXhNecQ?si=96UGKVcRTwJnP6RO')
    data
    # extract('https://youtube.com/playlist?list=PLeLN0qH0-mCVQKZ8-W1LhxDcVlWtTALCS&si=7oLwYupZV_3FKBnd')


if __name__ == '__main__':
    test_extract()
