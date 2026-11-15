# 5.7 · Wire it up and try it

**Time:** 40 minutes · **Before this:** [5.6](06-scenarios-and-runs.md).

## 📖 Read

Your ViewSets exist, but no address leads to them yet. In lesson 4.8 you wrote
`config/urls.py`, the project's address book. Now it gets the new addresses.

A **router** writes most of them for you. You say "businesses go to `BusinessViewSet`",
and the router makes both `businesses/` (list, create) and `businesses/<id>/` (one
business), plus the extra `businesses/<id>/assumptions/` from `@action`.

Components are different: their address has **two** ids
(`businesses/<business id>/components/<component id>/`). The router can't make that, so
we write those two addresses by hand, with `as_view`, which says "for this HTTP method,
call this action".

## ⌨️ Do

### 1. `config/urls.py` (for now)

Replace the whole file with the version from
[`for-now/config/urls.py`](for-now/config/urls.py):

<!-- source: self-learning-guide/05-business-and-api/for-now/config/urls.py:1-47 -->
```python
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from accounts import api as accounts_api
from businesses import api as businesses_api
from simulations import api as simulations_api

from . import views

# One router for the whole JSON API; each app's ViewSets are registered here.
router = DefaultRouter()
router.register("organizations", accounts_api.OrganizationViewSet, basename="organization")
router.register("businesses", businesses_api.BusinessViewSet, basename="business")
router.register("scenarios", simulations_api.ScenarioViewSet, basename="scenario")
router.register("runs", simulations_api.SimulationRunViewSet, basename="run")

# Components live under their business: /businesses/<id>/components/. Wired by hand
# (rather than a nested-router package) so the mapping is visible.
components_list = businesses_api.ComponentViewSet.as_view({"get": "list", "post": "create"})
components_detail = businesses_api.ComponentViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

api_v1 = [
    path("me/", accounts_api.me, name="me"),
    path("scenario-templates/", simulations_api.scenario_templates, name="scenario-templates"),
    path("inputs/", simulations_api.input_catalog, name="inputs"),
    path("businesses/<uuid:business_pk>/components/", components_list, name="component-list"),
    path(
        "businesses/<uuid:business_pk>/components/<uuid:pk>/",
        components_detail,
        name="component-detail",
    ),
    path("", include(router.urls)),
]

urlpatterns = [
    # A temporary home page. Part 10 replaces it with the real operations board.
    path("", login_required(TemplateView.as_view(template_name="home.html")), name="home"),
    path("accounts/", include("accounts.urls")),
    path("api/v1/", include((api_v1, "api"), namespace="api")),
    path("admin/", admin.site.urls),
    path("healthz/", views.healthz, name="healthz"),
]
```

```bash
python manage.py check
```

### 2. Run the server and log in

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** and log in (or sign up). Then open
**http://127.0.0.1:8000/api/v1/**. You'll see the router's list of addresses as JSON.

### 3. Open the browser console

Go back to **http://127.0.0.1:8000/** and press **F12** (on a Mac: **Cmd + Option + J**).
Click the **Console** tab. This is a place to type JavaScript that runs inside the page,
**logged in as you**.

> Chrome may say *"Don't paste code you don't understand"*. That's a good warning in
> general. Type `allow pasting` and press Enter, then paste. You understand this code:
> it's explained below.

Paste this small helper and press **Enter**:

<!-- source: self-learning-guide/05-business-and-api/practice/api_helper.js:1-17 -->
```js
function csrfToken() {
  return document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)?.[1];
}

async function api(method, url, body) {
  const response = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  console.log(response.status, data);
  return data;
}

console.log("api() helper ready");
```

It's also in [`practice/api_helper.js`](practice/api_helper.js).

### 4. Talk to your API

Type each line and press **Enter**. Read the answer before going on.

**Create a business:**

```js
const shop = await api("POST", "/api/v1/businesses/", {mode: "operating", name: "Kirana Express"})
```

→ `201` and the new business. `shop.id` now holds its id.

**List your businesses:**

```js
await api("GET", "/api/v1/businesses/")
```

**Save some numbers:**

```js
await api("PUT", `/api/v1/businesses/${shop.id}/assumptions/`, {assumptions: [{key: "daily_orders", value: "2400"}, {key: "contribution_margin", value: "22.5", source: "illustrative"}]})
```

→ `200`. Look at each number's `unit`: you never sent it, the catalogue did.
(The backticks `` ` `` make a **template string**: `${shop.id}` is replaced by the id.)

**Break a rule on purpose:**

```js
await api("PUT", `/api/v1/businesses/${shop.id}/assumptions/`, {assumptions: [{key: "conversion_rate", value: "3"}]})
```

→ `400`, with `error.code` = `"validation_error"` and, in `error.fields`, *"doesn't apply
to a business in 'operating' mode"*. Conversion rate is for ideas.

**Add two parts, one depending on the other:**

```js
await api("POST", `/api/v1/businesses/${shop.id}/components/`, {key: "payment-gateway", name: "Payment gateway", kind: "payment", criticality: 5})
```

```js
await api("POST", `/api/v1/businesses/${shop.id}/components/`, {key: "checkout", name: "Checkout", kind: "storefront", depends_on: ["payment-gateway"]})
```

→ both `201`. The second shows `depends_on: ["payment-gateway"]`.

**Ask a "what if?" question:**

```js
await api("POST", "/api/v1/scenarios/", {business: shop.id, template_key: "payment_gateway_outage", name: "Gateway down at dinner"})
```

→ `201`. Look at `parameters`: every setting got its default. And `missing_inputs` lists
the numbers you still need before Part 6 can run it (`average_order_value`,
`primary_gateway_share`, `recapture_rate`).

**Read the catalogue:** just open these in a new tab:

- **http://127.0.0.1:8000/api/v1/scenario-templates/**
- **http://127.0.0.1:8000/api/v1/inputs/**

**Archive the business:**

```js
await api("DELETE", `/api/v1/businesses/${shop.id}/`)
```

→ `204`. List again: it's gone. Now try `/api/v1/businesses/?archived=true`: it's still
there, just archived.

Stop the server with **Ctrl + C** when you're done.

## ✅ Check

- `python manage.py check` shows no issues.
- Every request above gives the status code shown.
- Errors always have the same shape: `{"error": {"code": ..., "message": ..., "fields": ...}}`.

## 🔍 Line by line

### `config/urls.py` (for now)

What's new since lesson 4.8:

- **Lines 7–9** · Import the three apps' `api` modules under short names.
- **Line 14** · One `DefaultRouter` for the whole API.
- **Line 15** · Organizations, as in Part 4.
- **Lines 16–18** · Register three more ViewSets: `register(prefix, ViewSet,
  basename=...)`. The prefix is the address part, the `basename` names the URLs
  (`business-list`, `business-detail`...).
- **Lines 20–21** · Comment: components are wired by hand, so you can see the mapping.
- **Line 22** · `as_view({...})` makes a view out of the ViewSet: GET → `list`, POST →
  `create`.
- **Lines 23–25** · The same for one component: GET → `retrieve`, PATCH →
  `partial_update`, DELETE → `destroy`.
- **Line 28** · `/api/v1/me/` from Part 4.
- **Lines 29–30** · The two catalogue addresses.
- **Line 31** · `<uuid:business_pk>` is a **path converter**: it accepts only a valid
  UUID and passes it to the view as `business_pk` (that's the `self.kwargs["business_pk"]`
  in lesson 5.5).
- **Lines 32–36** · One component: two converters in one address.
- **Line 37** · Everything the router made, added at the end. `include` adds a whole
  list of addresses at once.
- **Lines 40–47** · The same as Part 4.

### `api_helper.js`

Two JavaScript words first. **`fetch(url, options)`** is the browser's built-in way to
send an HTTP request from code. Talking to a server takes time, so `fetch` doesn't give
the answer straight away; **`await`** means "wait here until the answer arrives". A
function that uses `await` must be marked **`async`**.

- **Lines 1–3** · `csrfToken()` reads the CSRF token from the browser's cookies. Django
  needs it on every request that **changes** something (POST, PUT, PATCH, DELETE), to
  prove the request came from your own page (lesson 4.3). `.match(...)` searches the
  cookie text with a **regular expression** (a search pattern) for `csrftoken=...`, and
  `?.[1]` takes the value, or `undefined` if there isn't one. It's a function, so it
  reads the **current** token every time (logging in changes it).
- **Line 5** · `api(method, url, body)`: our helper. `body` is optional.
- **Line 6** · Send the request and wait for the answer.
- **Line 7** · Which method: `method` alone is short for `method: method`.
- **Line 8** · Two headers: "my body is JSON", and the CSRF token.
- **Line 9** · If there's a body, turn the JavaScript object into JSON text
  (`JSON.stringify`); otherwise send none. `a ? b : c` means "if a then b, else c".
- **Line 11** · Read the answer as text, and wait for it. (A 204 answer has none.)
- **Line 12** · Turn the text into an object with `JSON.parse`, or `null` if it's empty.
- **Line 13** · Print the status code and the data.
- **Line 14** · Also return the data, so you can keep it: `const shop = await api(...)`.
- **Line 17** · A message so you know the helper is ready.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `403` with `"code": "not_authenticated"` | You're not logged in. Log in at **http://127.0.0.1:8000/** in the **same** tab. |
| `403` with *"CSRF Failed"* | Reload the page (F5) so the browser has a fresh token cookie, then try again. |
| `404` on `/api/v1/businesses/` | Compare `config/urls.py` with the version above. |
| `500` and a long error in the terminal | Read the **last** line of the error in the terminal running `runserver`; it names the file and line. |
| `SyntaxError: await is only valid in async functions` | Some browsers only allow `await` at the top of the console. Use Chrome, Edge or Firefox. |

## ❓ Quiz

1. Why are the component addresses written by hand?
2. What does `<uuid:business_pk>` do with `/businesses/hello/components/`?
3. Why does the helper send `X-CSRFToken`?

---

**Next:** [5.8 · Tests and commit](08-tests-and-commit.md)

<details><summary>Quiz answers</summary>

1. They have two ids (business and component); the simple router only makes one-id
   addresses. Writing them by hand also makes the mapping easy to see.
2. `hello` isn't a UUID, so the address doesn't match at all: 404, and the view never
   runs.
3. Django refuses changing requests without a CSRF token, so another website can't make
   your browser change your data.

</details>
