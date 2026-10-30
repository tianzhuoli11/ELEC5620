# Source deployment rehearsal

The primary demonstration route remains Python 3.11+ and a virtual environment. Docker is an additional reproducible route; it is not required on the demonstration computer.

## Python route

Unzip the final Canvas source into a short clean path. Create a new venv, install `requirements.txt`, run `python -m pip check` and `python -m unittest discover -s tests -q`, then `python -m streamlit run app.py`. Use that environment's Python for every command. Run the five page scenarios described by the domain docs. Set the already-provided campus API key locally and connect to campus/VPN for optional AI; offline simulated paths need no key.

## Docker route

```sh
docker build -t haven:demo .
docker run --rm -p 127.0.0.1:8501:8501 haven:demo
```

Open `http://127.0.0.1:8501`. The image runs as a non-root user and has an HTTP health check. Local keys, `.env`, runtime records, git history and environments are excluded from the build context. Do not add a secret with `ARG`, `ENV` in the Dockerfile, or `COPY`.

To use an existing shell key without embedding it in the image:

```sh
docker run --rm -p 127.0.0.1:8501:8501 -e ELEC5620_API_KEY haven:demo
```

The shell variable must already exist. Host VPN access does not guarantee the container can reach the campus subnet: test that path separately. For reliable on-site AI, prefer the verified host Python route. Container logs and safety state are temporary unless you explicitly mount a writable `data/runtime` directory. Each new browser session starts with unknown safety clearance and must run the safety pages before Energy control.

## Automated verification

Verified execution on 30 October: [Actions run 41048545525](https://github.com/tianzhuoli11/ELEC5620/actions/runs/41048545525), source `986de17`. Python 3.11/3.13 jobs, image build, container startup/health and the in-container repository suite all passed. Earlier container tests exposed fixtures writing temporary files into the read-only source root; those fixtures now use the system temporary directory. The fix preserves non-root execution rather than granting broad source-directory write access.

`.github/workflows/ci.yml` runs the offline suite on Python 3.11 and 3.13, uploads a deterministic fault-evaluation artifact, builds Docker, checks the container health endpoint and runs all offline tests inside it. Public CI does not receive the personal campus key or claim live VPN connectivity. Actual run URLs and conclusions belong in the evidence documentation after completion, not before it.

The final required rehearsal is still the exact archive uploaded to Canvas on the demonstration machine. A CI build from a branch cannot certify a different submission archive or the venue network.
