"""Lažni Firebase za testove: isti REST kao pravi (prijava, Firestore dokumenti), u memoriji, bez interneta.
Pokretanje za ručne probe: python lazni_firebase.py 8790"""
import json
import secrets
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Stanje:
    def __init__(self):
        self.dok = {}            # puna putanja -> {polje: vrednost}
        self.tokeni = set()
        self.bez_mreze = False   # glumi da nema interneta
        self.zahtevi = 0


def napravi_server(port=0):
    st = Stanje()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")

        def _odgovor(self, kod, telo=None):
            sadrzaj = json.dumps(telo if telo is not None else {}).encode()
            self.send_response(kod)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(sadrzaj)))
            self.end_headers()
            self.wfile.write(sadrzaj)

        def _telo(self):
            n = int(self.headers.get("Content-Length") or 0)
            sirovo = self.rfile.read(n) if n else b""
            if "x-www-form-urlencoded" in (self.headers.get("Content-Type") or ""):
                return dict(urllib.parse.parse_qsl(sirovo.decode()))
            return json.loads(sirovo or b"{}")

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.end_headers()

        def _obradi(self, metod):
            st.zahtevi += 1
            if st.bez_mreze:
                self.connection.close()          # kao da nema interneta
                return
            url = urllib.parse.urlparse(self.path)
            if url.path == "/v1/accounts:signUp":
                t = "tok" + secrets.token_hex(8)
                st.tokeni.add(t)
                return self._odgovor(200, dict(idToken=t, refreshToken="r" + t, expiresIn="3600", localId="u1"))
            if url.path == "/v1/token":
                rt = self._telo().get("refresh_token", "")
                t = rt[1:]
                st.tokeni.add(t)
                return self._odgovor(200, dict(id_token=t, refresh_token=rt, expires_in="3600"))
            if "/documents/" not in url.path:
                return self._odgovor(404, {"error": {"message": "nema"}})
            if (self.headers.get("Authorization") or "")[7:] not in st.tokeni:
                return self._odgovor(403, {"error": {"message": "Missing or insufficient permissions."}})
            put = urllib.parse.unquote(url.path.split("/documents/", 1)[1])
            delovi = put.split("/")
            if len(delovi) < 2 or delovi[0] != "farme" or len(delovi[1]) < 40:
                return self._odgovor(403, {"error": {"message": "Missing or insufficient permissions."}})
            ime = lambda p: "projects/x/databases/(default)/documents/" + p
            if metod == "PATCH":
                polja = self._telo().get("fields", {})
                if len(json.dumps(polja)) > 1_048_000:
                    return self._odgovor(400, {"error": {"message": "Document exceeds maximum size"}})
                st.dok[put] = {k: v.get("stringValue", "") for k, v in polja.items()}
                return self._odgovor(200, dict(name=ime(put)))
            if metod == "DELETE":
                st.dok.pop(put, None)
                return self._odgovor(200, {})
            if len(delovi) % 2 == 0:              # dokument
                if put not in st.dok:
                    return self._odgovor(404, {"error": {"message": "not found"}})
                return self._odgovor(200, dict(name=ime(put), fields={k: {"stringValue": v} for k, v in st.dok[put].items()}))
            pref = put + "/"                      # lista kolekcije
            imena = sorted(k for k in st.dok if k.startswith(pref) and "/" not in k[len(pref):])
            q = urllib.parse.parse_qs(url.query)
            vel, od = int(q.get("pageSize", ["300"])[0]), int(q.get("pageToken", ["0"])[0])
            strana = imena[od:od + vel]
            telo = dict(documents=[dict(name=ime(k), fields={a: {"stringValue": b} for a, b in st.dok[k].items()}) for k in strana]) if strana else {}
            if od + vel < len(imena):
                telo["nextPageToken"] = str(od + vel)
            return self._odgovor(200, telo)

        def do_GET(self):
            self._obradi("GET")

        def do_POST(self):
            self._obradi("POST")

        def do_PATCH(self):
            self._obradi("PATCH")

        def do_DELETE(self):
            self._obradi("DELETE")

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    konfig = dict(apiKey="test", projectId="x", authUrl=url, tokenUrl=url, firestoreUrl=url)
    return srv, st, konfig


if __name__ == "__main__":
    srv, st, k = napravi_server(int(sys.argv[1]) if len(sys.argv) > 1 else 8790)
    print("lažni Firebase:", k, flush=True)
    threading.Event().wait()
