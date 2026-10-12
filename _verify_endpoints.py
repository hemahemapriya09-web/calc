import json
import os
import urllib.error
import urllib.request

# Point the suite at any deployment:
#   set CALC_BASE_URL=https://your-app.example.com
BASE = os.environ.get("CALC_BASE_URL", "http://127.0.0.1:5000").rstrip("/")

failures = []


def check(label, actual, expected):
    ok = actual == expected
    print(("PASS  " if ok else "FAIL  ") + label + " -> " + repr(actual))
    if not ok:
        failures.append(label + ": expected " + repr(expected) + ", got " + repr(actual))


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as response:
        return response.status, response.read().decode("utf-8")


def post(payload):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        BASE + "/calculate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


status, html = get("/")
check("GET / status", status, 200)
check("GET / serves calculator", "Scientific Calculator" in html, True)
check("GET / has keys grid", 'class="keys"' in html, True)
check("GET / css min-height fixed", "min-height: 49px" in html, True)
check("GET / posts to /calculate", 'fetch("/calculate"' in html, True)
check("GET / has favicon link", 'rel="icon"' in html, True)
check("GET / sets Error on failure", 'display.value = "Error"' in html, True)
check("GET / resets error before calc", "    resetIfError();\n\n    const expression" in html, True)

status, data = post({"expression": "2+3*4", "mode": "DEG"})
check("2+3*4", (status, data), (200, {"result": 14}))

status, data = post({"expression": "sqrt(16)", "mode": "DEG"})
check("sqrt(16)", (status, data), (200, {"result": 4.0}))

status, data = post({"expression": "sin(30)", "mode": "DEG"})
check("sin(30) DEG", (status, round(data.get("result", -99), 10)), (200, 0.5))

status, data = post({"expression": "sin(pi/2)", "mode": "RAD"})
check("sin(pi/2) RAD", (status, round(data.get("result", -99), 10)), (200, 1.0))

status, data = post({"expression": "log(1000)", "mode": "DEG"})
check("log(1000)", (status, round(data.get("result", -99), 10)), (200, 3.0))

status, data = post({"expression": "ln(e)", "mode": "DEG"})
check("ln(e)", (status, round(data.get("result", -99), 10)), (200, 1.0))

status, data = post({"expression": "2**10", "mode": "DEG"})
check("2**10", (status, data), (200, {"result": 1024}))

status, data = post({"expression": "10%3", "mode": "DEG"})
check("10%3", (status, data), (200, {"result": 1}))

status, data = post({"expression": "-(7)", "mode": "DEG"})
check("-(7)", (status, data), (200, {"result": -7}))

status, data = post({"expression": "asin(1)", "mode": "DEG"})
check("asin(1) DEG", (status, round(data.get("result", -99), 10)), (200, 90.0))

status, data = post({"expression": "1/0", "mode": "DEG"})
check("1/0 rejected", (status, data.get("error")), (400, "Cannot divide by zero."))

status, data = post({"expression": "__import__('os')", "mode": "DEG"})
check("code injection rejected", (status, "error" in data), (400, True))

status, data = post({"expression": "1+", "mode": "DEG"})
check("syntax error rejected", (status, "error" in data), (400, True))

status, data = post({"expression": "sqrt(-1)", "mode": "DEG"})
check("domain error rejected", (status, "error" in data), (400, True))

status, data = post({"expression": "tan(90)", "mode": "DEG"})
check("tan(90) undefined", (status, "error" in data), (400, True))

status, data = post({"expression": "2+2", "mode": "BOGUS"})
check("bad mode rejected", (status, "error" in data), (400, True))

status, data = post({"expression": "2+2", "mode": "RAD"})
check("explicit RAD ok", (status, data), (200, {"result": 4}))

print()
print("TOTAL FAILURES: " + str(len(failures)))
for failure in failures:
    print(" - " + failure)
