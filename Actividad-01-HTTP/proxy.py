import socket
import json
import sys

def p_h_m(h_m_b):
    p = h_m_b.split(b'\r\n\r\n', 1)
    h_t = p[0].decode('utf-8')

    if len(p) > 1:
        b_b = p[1]
    else:
        b_b = b""

    l = h_t.split('\r\n')
    s_l = l[0]
    h_d = {}

    for ln in l[1:]:
        if ": " in ln:
            ll, v = ln.split(': ', 1)
            h_d[ll] = v

    d_f = {
        "s_l": s_l,
        "h_d": h_d,
        "b_b": b_b
    }
    return d_f

def c_h_m(d_d):
    m_t = d_d["s_l"] + "\r\n"

    for ll in d_d["h_d"]:
        m_t += ll + ": " + d_d["h_d"][ll] + "\r\n"

    m_t += "\r\n"
    m_f_b = m_t.encode('utf-8') + d_d["b_b"]

    return m_f_b

def c_e_o_m(m_b, e_s):
    return e_s in m_b

def r_f_m(c_s, b_s, e_s):
    r_m = c_s.recv(b_s)
    f_m = r_m

    i_e_o_m = c_e_o_m(f_m, e_s)

    while not i_e_o_m:
        r_m = c_s.recv(b_s)
        if r_m == b"":
            break
        f_m += r_m
        i_e_o_m = c_e_o_m(f_m, e_s)

    if f_m == b"":
        return b""

    p = f_m.split(e_s, 1)
    h_t = p[0].decode('utf-8')

    if len(p) > 1:
        b_p = p[1]
    else:
        b_p = b""

    c_l = 0
    l_c = h_t.split('\r\n')

    for ln in l_c:
        if "content-length:" in ln.lower():
            p_l = ln.split(':')
            c_l = int(p_l[1].strip())

    b_f = c_l - len(b_p)

    while b_f > 0:
        r_m = c_s.recv(b_s)
        if r_m == b"":
            break
        f_m += r_m
        b_f -= len(r_m)

    return f_m


if __name__ == "__main__":
    with open(sys.argv[1], 'r') as a_j:
        c = json.load(a_j)

    n_u = c["user"]
    b_l = c["blocked"]
    p_p = c["forbidden_words"]

    b_s = 50
    e_o_m = b"\r\n\r\n"
    s_s_a = ('127.0.0.1', 8000)

    print('Creando socket - Servidor')
    s_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s_s.bind(s_s_a)
    s_s.listen(10)

    print('... Esperando clientes')

    while True:
        n_s, n_s_a = s_s.accept()
        r_m = r_f_m(n_s, b_s, e_o_m)

        if r_m == b"":
            n_s.close()
            continue

        p_r = p_h_m(r_m)

        if "Host" not in p_r["h_d"]:
            n_s.close()
            continue

        h_h = p_r["h_d"]["Host"]
        h_d = h_h.split(':')[0]

        p_s_l = p_r["s_l"].split(' ')
        pt = p_s_l[1]

        if "images.jpg" in pt:
            with open("images.jpg", "rb") as a_i:
                b_i = a_i.read()

            r_i = {
                "s_l": "HTTP/1.1 200 OK",
                "h_d": {
                    "Content-Type": "image/jpeg",
                    "Content-Length": str(len(b_i))
                },
                "b_b": b_i
            }
            n_s.send(c_h_m(r_i))
            n_s.close()
            continue

        e_b = False
        for p_m in b_l:
            if p_m in h_d or p_m in pt:
                e_b = True
                break

        if e_b:
            print("[-] Bloqueando " + h_d)
            t_h = "<html><body><h1>403 Forbidden</h1><img src='images.jpg'></body></html>".encode('utf-8')

            r_403 = {
                "s_l": "HTTP/1.1 403 Forbidden",
                "h_d": {
                    "Content-Type": "text/html",
                    "Content-Length": str(len(t_h)),
                    "Connection": "close"
                },
                "b_b": t_h
            }
            n_s.send(c_h_m(r_403))
            n_s.close()
            continue

        p_r["h_d"]["X-ElQuePregunta"] = n_u
        p_r["h_d"]["Connection"] = "close"

        c_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c_s.connect((h_d, 80))

        s_m = c_h_m(p_r)
        c_s.send(s_m)

        m_f_s = r_f_m(c_s, b_s, e_o_m)
        c_s.close()

        if m_f_s != b"":
            p_rs = p_h_m(m_f_s)

            if "Content-Type" in p_rs["h_d"]:
                t_c = p_rs["h_d"]["Content-Type"]

                if "text" in t_c or "html" in t_c:
                    t_p = p_rs["b_b"].decode('utf-8')

                    for r_d in p_p:
                        for p_o, p_r3 in r_d.items():
                            t_p = t_p.replace(p_o, p_r3)

                    p_rs["b_b"] = t_p.encode('utf-8')
                    n_l = len(p_rs["b_b"])
                    p_rs["h_d"]["Content-Length"] = str(n_l)

            m_f = c_h_m(p_rs)
            n_s.send(m_f)

        n_s.close()