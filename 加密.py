def main(params):
    import base64
    import hashlib
    import json
    import urllib.parse

    # 1. 将 RequestData 和 ApiKey 拼接
    request_data = {"LogisticCode": f"{params.get('logistic_code')}"}
    api_key = "4c5302d2-3b8e-4afe-9028-b2e01a27f49b"
    combined_data = json.dumps(request_data) + api_key

    # 2. MD5 加密并转换成小写
    md5_hash = hashlib.md5(combined_data.encode("utf-8")).hexdigest()

    # 3. Base64 编码
    base64_encoded = base64.b64encode(md5_hash.encode("utf-8")).decode("utf-8")

    # 4. URL 编码
    url_encoded = urllib.parse.quote(base64_encoded)

    return {
        "RequestType": 8002,
        "EBusinessID": 1583419,
        "DataSign": url_encoded,
        "RequestData": urllib.parse.quote(json.dumps(request_data)),
    }
