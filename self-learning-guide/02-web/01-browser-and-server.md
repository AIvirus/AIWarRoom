# 2.1 · Browser, server, request, response

**Time:** 30 minutes · **Before this:** [Part 1](../01-python/README.md).

## Read

When you open a website, two computers talk to each other:

| | Who | Job |
|---|---|---|
| **Client** | Your **browser** (Chrome, Firefox...) | Asks for pages and shows them |
| **Server** | A program on a computer somewhere | Listens for requests and sends back answers |

It works like ordering at a restaurant counter:

1. You (the **browser**) say: *"One masala dosa, please."* That's a **request**.
2. The kitchen (the **server**) makes it.
3. You get the dosa back on a plate. That's the **response**.

### What a request contains

- An **address (URL)**, like `http://127.0.0.1:8000/runs/5/`:
  - `http://` is the **protocol** (the language of the conversation: HTTP).
  - `127.0.0.1` is the **host**, which computer to talk to. `127.0.0.1` (also called
    `localhost`) always means **this same computer**.
  - `8000` is the **port**, which program on that computer. One computer can run many
    servers, each listening on its own port number.
  - `/runs/5/` is the **path**, which page you want.
- A **method**: what you want to do.
  - `GET` = "please give me this" (opening a page).
  - `POST` = "please take this data" (submitting a form).
  - `PATCH`, `PUT` = "please change this"; `DELETE` = "please remove this".

### What a response contains

- A **status code**: a 3-digit number saying how it went.

  | Code | Means |
  |---|---|
  | `200` | OK, here it is |
  | `201` | Created (something new was saved) |
  | `302` | Go to another address instead (a redirect) |
  | `400` | Your request has a mistake |
  | `403` | You're not allowed |
  | `404` | Not found |
  | `500` | The server itself broke (a bug) |

- The **content**: the web page, picture or data.

In AI WarRoom, **Django** is the server. Your browser sends requests; Django runs Python
code and sends back pages.

## Do

Python can run a very simple web server that just sends files from a folder.

1. Make a folder `web` in your `learning` folder and go into it in the terminal.
2. Create `index.html` there with the content from lesson 2.2. For now, just copy it
   from [`practice/index.html`](practice/index.html); 2.2 explains every line.
3. Start the server:

```bash
python -m http.server 8765
```

4. Open your browser at **http://localhost:8765/index.html**.
5. Look back at the terminal. Each request has printed a line.
6. Now open **http://localhost:8765/nothing-here.html**.
7. Stop the server with **Ctrl + C**.

## Check

The terminal shows lines like these (your date and time will differ):

```text
127.0.0.1 - - [15/Nov/2026 11:21:54] "GET /index.html HTTP/1.1" 200 -
127.0.0.1 - - [15/Nov/2026 11:21:54] "GET /style.css HTTP/1.1" 404 -
127.0.0.1 - - [15/Nov/2026 11:22:10] "GET /nothing-here.html HTTP/1.1" 404 -
```

Notice: opening **one** page made the browser send **several** requests, one for the page
and one for each file the page needs (like `style.css`). The missing ones got `404`. Once
you create `style.css` and `app.js` in lesson 2.2, they'll get `200` too.

## Line by line

| Part | Meaning |
|---|---|
| `python -m http.server 8765` | Run Python's built-in module `http.server`, listening on port `8765`. It sends any file in the current folder to whoever asks. |
| `127.0.0.1` | The address of the computer that sent the request: yours. |
| `"GET /index.html HTTP/1.1"` | The request: method `GET`, path `/index.html`, protocol version `HTTP/1.1`. |
| `200` / `404` | The status code the server answered with. |

## If it didn't work

| You see | Fix |
|---|---|
| `OSError: [Errno 98] Address already in use` (or `10048` on Windows) | Another program uses port 8765. Pick another number: `python -m http.server 8800`. |
| The browser says "This site can't be reached" | The server isn't running, or you typed a different port. |
| You get a list of files instead of your page | You opened `http://localhost:8765/` without `index.html`; click `index.html`. |

## Quiz

1. Which one is the client: the browser or the server?
2. What does status code `404` mean? And `500`?
3. In `http://127.0.0.1:8000/runs/5/`, what is `8000`?

---

**Next:** [2.2 · HTML, CSS and JavaScript](02-html-css-javascript.md)

<details><summary>Quiz answers</summary>

1. The browser.
2. 404 = not found. 500 = the server broke (a bug on the server's side).
3. The port: which program on that computer to talk to.

</details>
