# User Guide

```mdstorm-setup
--vcr-opts '{"record_mode": "none"}'
```

```mdstorm --mock-http mocks/cassette.yaml
$resp=$lib.inet.http.get("http://example.com") [ it:dev:str=$resp.body.decode() ]
```
