import test_client
import test_request


def test_suite():
    return unittest.makeSuite([test_client.TestClient])
