import urllib.request
import json
import uuid

def test_get_documents():
    print("Testing GET /documents...")
    try:
        req = urllib.request.Request("http://127.0.0.1:8501/documents")
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode('utf-8')
            print(f"Status: {status}")
            print(f"Body: {body}")
            assert status == 200
            return json.loads(body)["documents"]
    except Exception as e:
        print(f"Failed to test GET /documents: {e}")
        return []

def test_upload():
    print("\nTesting POST /upload...")
    # Create multipart form-data request manually or using a boundary
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    filename = f"test_doc_{uuid.uuid4().hex[:6]}.txt"
    content = "This is a mock test document for verification of RAG search agent migration."
    
    parts = []
    parts.append(f"--{boundary}")
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"')
    parts.append("Content-Type: text/plain")
    parts.append("")
    parts.append(content)
    parts.append(f"--{boundary}--")
    parts.append("")
    
    body_data = "\r\n".join(parts).encode('utf-8')
    
    req = urllib.request.Request(
        "http://127.0.0.1:8501/upload",
        data=body_data,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode('utf-8')
            print(f"Status: {status}")
            print(f"Body: {body}")
            assert status == 200
            res = json.loads(body)
            assert res["filename"] == filename
            print(f"Successfully uploaded and indexed mock doc: {filename}")
    except Exception as e:
        print(f"Failed to test POST /upload: {e}")

def test_query_stream():
    print("\nTesting POST /query (SSE streaming)...")
    data = json.dumps({
        "prompt": "Say hello world briefly",
        "history": []
    }).encode('utf-8')
    
    req = urllib.request.Request(
        "http://127.0.0.1:8501/query",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            print(f"Status: {status}")
            print("Streaming content:")
            for line in response:
                decoded_line = line.decode('utf-8').strip()
                if decoded_line:
                    print(decoded_line)
    except Exception as e:
        print(f"Failed to test POST /query: {e}")

if __name__ == "__main__":
    docs_before = test_get_documents()
    test_upload()
    docs_after = test_get_documents()
    assert len(docs_after) > len(docs_before)
    test_query_stream()
    
    # Delete uploaded document
    print("\nTesting POST /delete...")
    new_docs = [d for d in docs_after if d not in docs_before]
    if new_docs:
        doc_to_delete = new_docs[0]
        data = json.dumps({"filename": doc_to_delete}).encode('utf-8')
        req = urllib.request.Request(
            "http://127.0.0.1:8501/delete",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as response:
                status = response.status
                body = response.read().decode('utf-8')
                print(f"Status: {status}")
                print(f"Body: {body}")
                assert status == 200
                print(f"Successfully deleted document: {doc_to_delete}")
        except Exception as e:
            print(f"Failed to test POST /delete: {e}")
            raise e
            
    docs_final = test_get_documents()
    assert len(docs_final) == len(docs_before)
    print("\nAll integration tests passed successfully!")
