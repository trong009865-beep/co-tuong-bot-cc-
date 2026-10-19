
import copy
import json
import random
import streamlit as st

st.set_page_config(page_title="Cờ Tướng", page_icon="♟️", layout="wide")

# Ký hiệu: chữ hoa là Đỏ, chữ thường là Đen
SYMBOL = {
    "K": "帥", "A": "仕", "E": "相", "R": "俥",
    "H": "傌", "C": "炮", "P": "兵",
    "k": "將", "a": "士", "e": "象", "r": "車",
    "h": "馬", "c": "砲", "p": "卒",
}
VALUE = {"K": 10000, "A": 120, "E": 120, "R": 600,
         "H": 300, "C": 350, "P": 70}

def new_board():
    b = [["." for _ in range(9)] for _ in range(10)]
    back = list("rheakaehr")
    for c, p in enumerate(back):
        b[0][c] = p
        b[9][c] = p.upper()
    for c in (1, 7):
        b[2][c] = "c"
        b[7][c] = "C"
    for c in (0, 2, 4, 6, 8):
        b[3][c] = "p"
        b[6][c] = "P"
    return b

def side(p):
    return "R" if p.isupper() else "B"

def inside(r, c):
    return 0 <= r < 10 and 0 <= c < 9

def palace(r, c, red):
    return 7 <= r <= 9 and 3 <= c <= 5 if red else 0 <= r <= 2 and 3 <= c <= 5

def pseudo(b, r, c):
    p = b[r][c]
    if p == ".":
        return []
    red = p.isupper()
    enemy = "B" if red else "R"
    kind = p.upper()
    out = []

    def add(nr, nc):
        if inside(nr, nc) and (b[nr][nc] == "." or side(b[nr][nc]) == enemy):
            out.append((nr, nc))

    if kind == "R" or kind == "C":
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = r + dr, c + dc
            screened = False
            while inside(nr, nc):
                target = b[nr][nc]
                if kind == "R":
                    if target == ".":
                        out.append((nr, nc))
                    else:
                        if side(target) == enemy:
                            out.append((nr, nc))
                        break
                else:
                    if not screened:
                        if target == ".":
                            out.append((nr, nc))
                        else:
                            screened = True
                    elif target != ".":
                        if side(target) == enemy:
                            out.append((nr, nc))
                        break
                nr += dr
                nc += dc

    elif kind == "H":
        for dr, dc, lr, lc in (
            (2,1,1,0),(2,-1,1,0),(-2,1,-1,0),(-2,-1,-1,0),
            (1,2,0,1),(1,-2,0,-1),(-1,2,0,1),(-1,-2,0,-1)
        ):
            nr, nc = r + dr, c + dc
            if inside(nr, nc) and b[r+lr][c+lc] == ".":
                add(nr, nc)

    elif kind == "E":
        for dr, dc in ((2,2),(2,-2),(-2,2),(-2,-2)):
            nr, nc = r + dr, c + dc
            eye_r, eye_c = r + dr//2, c + dc//2
            if inside(nr, nc) and b[eye_r][eye_c] == ".":
                if (red and nr >= 5) or (not red and nr <= 4):
                    add(nr, nc)

    elif kind == "A":
        for dr, dc in ((1,1),(1,-1),(-1,1),(-1,-1)):
            nr, nc = r + dr, c + dc
            if inside(nr, nc) and palace(nr, nc, red):
                add(nr, nc)

    elif kind == "K":
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = r + dr, c + dc
            if inside(nr, nc) and palace(nr, nc, red):
                add(nr, nc)
        # Tướng có thể bắt tướng đối phương khi hai tướng đối mặt
        for dr in (-1, 1):
            nr = r + dr
            while inside(nr, c):
                if b[nr][c] != ".":
                    if b[nr][c].upper() == "K" and side(b[nr][c]) == enemy:
                        out.append((nr, c))
                    break
                nr += dr

    elif kind == "P":
        forward = -1 if red else 1
        add(r + forward, c)
        crossed = r <= 4 if red else r >= 5
        if crossed:
            add(r, c-1)
            add(r, c+1)
    return out

def find_king(b, red):
    k = "K" if red else "k"
    for r in range(10):
        for c in range(9):
            if b[r][c] == k:
                return (r, c)
    return None

def checked(b, red):
    king = find_king(b, red)
    if king is None:
        return True
    for r in range(10):
        for c in range(9):
            p = b[r][c]
            if p != "." and p.isupper() != red:
                if king in pseudo(b, r, c):
                    return True
    return False

def legal(b, red):
    moves = []
    for r in range(10):
        for c in range(9):
            p = b[r][c]
            if p != "." and p.isupper() == red:
                for nr, nc in pseudo(b, r, c):
                    target = b[nr][nc]
                    b[nr][nc], b[r][c] = p, "."
                    safe = not checked(b, red)
                    b[r][c], b[nr][nc] = p, target
                    if safe:
                        moves.append((r, c, nr, nc))
    return moves

def make_move(b, m):
    r, c, nr, nc = m
    captured = b[nr][nc]
    b[nr][nc] = b[r][c]
    b[r][c] = "."
    return captured

def evaluate(b):
    score = 0
    for r in range(10):
        for c in range(9):
            p = b[r][c]
            if p == ".":
                continue
            v = VALUE.get(p.upper(), 0)
            if p.upper() == "P":
                v += (6-r)*7 if p.isupper() else (r-3)*7
            score += v if p.isupper() else -v
    return score

def ordered_moves(b, moves):
    return sorted(moves, key=lambda m: (
        b[m[2]][m[3]] != ".",
        VALUE.get(b[m[2]][m[3]].upper(), 0)
        if b[m[2]][m[3]] != "." else 0
    ), reverse=True)

def search(b, depth, alpha, beta, red_turn):
    moves = legal(b, red_turn)
    if not moves:
        return (-100000 if red_turn else 100000), None
    if depth == 0:
        return evaluate(b), None

    best = None
    for m in ordered_moves(b, moves):
        old = b[m[2]][m[3]]
        make_move(b, m)
        score, _ = search(b, depth-1, alpha, beta, not red_turn)
        b[m[0]][m[1]] = b[m[2]][m[3]]
        b[m[2]][m[3]] = old

        if red_turn:
            if score > alpha:
                alpha, best = score, m
        else:
            if score < beta:
                beta, best = score, m
        if alpha >= beta:
            break
    return (alpha if red_turn else beta), best

def bot_move(b, level):
    depths = {"Dễ": 1, "Trung bình": 2, "Khó": 2, "Siêu khó": 3}
    moves = legal(b, True)
    if not moves:
        return None
    if level == "Dễ":
        return random.choice(moves)
    _, m = search(b, depths[level], -1000000, 1000000, True)
    return m or random.choice(moves)

def move_name(b, m):
    r, c, nr, nc = m
    p = b[r][c]
    return f"{'Đỏ' if p.isupper() else 'Đen'}: {SYMBOL[p]} ({r+1},{c+1}) → ({nr+1},{nc+1})"

def fresh_game(mode, level):
    st.session_state.board = new_board()
    st.session_state.turn = True  # True = Đỏ
    st.session_state.mode = mode
    st.session_state.level = level
    st.session_state.selected = None
    st.session_state.history = []
    st.session_state.snapshots = []
    st.session_state.over = False
    st.session_state.winner = None
    st.session_state.paused = False
    st.session_state.hint = None
    st.session_state.started = True

def snapshot():
    st.session_state.snapshots.append({
        "board": copy.deepcopy(st.session_state.board),
        "turn": st.session_state.turn,
        "history": list(st.session_state.history),
        "over": st.session_state.over,
        "winner": st.session_state.winner,
    })

def play(m):
    b = st.session_state.board
    snapshot()
    captured = make_move(b, m)
    st.session_state.history.append(
        move_name(copy.deepcopy(b), (m[2], m[3], m[0], m[1]))
        if False else f"{'Đỏ' if st.session_state.turn else 'Đen'}: "
        f"{SYMBOL[b[m[2]][m[3]]]} ({m[0]+1},{m[1]+1}) → ({m[2]+1},{m[3]+1})"
        + (f" ăn {SYMBOL[captured]}" if captured != "." else "")
    )
    st.session_state.turn = not st.session_state.turn
    st.session_state.selected = None
    st.session_state.hint = None
    if find_king(b, st.session_state.turn) is None or not legal(b, st.session_state.turn):
        st.session_state.over = True
        st.session_state.winner = "Đỏ" if not st.session_state.turn else "Đen"

# Khởi tạo trạng thái
if "started" not in st.session_state:
    st.session_state.started = False
if "lang" not in st.session_state:
    st.session_state.lang = "vi"
if "sound" not in st.session_state:
    st.session_state.sound = True
if "music" not in st.session_state:
    st.session_state.music = True
if "volume" not in st.session_state:
    st.session_state.volume = 70
if "stats" not in st.session_state:
    st.session_state.stats = {"Thắng": 0, "Thua": 0, "Hòa": 0}
if "settings" not in st.session_state:
    st.session_state.settings = False

EN = st.session_state.lang == "en"
def T(vi, en):
    return en if EN else vi

st.title("♟️ Chinese Chess" if EN else "♟️ CỜ TƯỚNG")
st.caption(T("Game cờ tướng — đấu máy hoặc đấu hai người", "Play against the computer or another player"))

if not st.session_state.started:
    st.subheader(T("Màn hình chính", "Main Menu"))
    mode = st.radio(T("Chế độ chơi", "Game mode"),
                    [T("Đấu với máy", "Play vs Computer"),
                     T("Đấu 2 người", "Two Players")])
    level = st.selectbox(T("Độ khó của bot", "Bot difficulty"),
                         ["Dễ", "Trung bình", "Khó", "Siêu khó"])
    col1, col2 = st.columns(2)
    with col1:
        if st.button(T("▶ Bắt đầu", "▶ Start Game"), type="primary", use_container_width=True):
            fresh_game("bot" if mode == T("Đấu với máy", "Play vs Computer") else "two", level)
            st.rerun()
    with col2:
        if st.button(T("⚙ Cài đặt", "⚙ Settings"), use_container_width=True):
            st.session_state.settings = not st.session_state.settings
    if st.session_state.settings:
        st.session_state.lang = st.radio(T("Ngôn ngữ", "Language"),
                                          ["vi", "en"],
                                          format_func=lambda x: "Tiếng Việt" if x == "vi" else "English",
                                          horizontal=True)
        st.session_state.volume = st.slider(T("Âm lượng", "Volume"), 0, 100, st.session_state.volume)
        st.session_state.music = st.toggle(T("Nhạc nền (tùy chọn)", "Background music (setting)"), st.session_state.music)
        st.session_state.sound = st.toggle(T("Hiệu ứng âm thanh", "Sound effects (setting)"), st.session_state.sound)
    st.stop()

# Bot Đỏ đi trước khi đấu máy
if (st.session_state.mode == "bot" and st.session_state.turn
        and not st.session_state.over and not st.session_state.paused):
    m = bot_move(st.session_state.board, st.session_state.level)
    if m:
        play(m)
    st.rerun()

coltitle, colgear = st.columns([5, 1])
with coltitle:
    st.subheader(T("Bàn cờ", "Chess Board"))
    if st.session_state.over:
        st.success(T(f"Ván đấu kết thúc! Bên thắng: {st.session_state.winner}",
                     f"Game over! Winner: {'Red' if st.session_state.winner == 'Đỏ' else 'Black'}"))
    elif st.session_state.paused:
        st.warning(T("Trận đấu đang tạm dừng", "Game paused"))
    else:
        st.info(T("Lượt Đỏ" if st.session_state.turn else "Lượt Đen",
                  "Red to move" if st.session_state.turn else "Black to move"))
with colgear:
    if st.button("⚙️", help=T("Cài đặt trong trận", "In-game settings"), use_container_width=True):
        st.session_state.settings = not st.session_state.settings

if st.session_state.settings:
    with st.container(border=True):
        st.markdown(T("### Cài đặt trận đấu", "### Game Settings"))
        if st.button(T("▶ Tiếp tục", "▶ Resume"), use_container_width=True):
            st.session_state.paused = False
            st.session_state.settings = False
            st.rerun()
        st.session_state.volume = st.slider(T("Âm lượng", "Volume"), 0, 100, st.session_state.volume)
        st.session_state.music = st.toggle(T("Nhạc nền", "Background music"), st.session_state.music)
        st.session_state.sound = st.toggle(T("Hiệu ứng âm thanh", "Sound effects"), st.session_state.sound)
        st.session_state.lang = st.radio(T("Ngôn ngữ", "Language"), ["vi", "en"],
            format_func=lambda x: "Tiếng Việt" if x == "vi" else "English",
            horizontal=True)
        if st.button(T("⏸ Tạm dừng", "⏸ Pause"), use_container_width=True):
            st.session_state.paused = True
            st.rerun()
        if st.button(T("🏠 Về màn hình chính", "🏠 Main Menu"), use_container_width=True):
            st.session_state.started = False
            st.session_state.settings = False
            st.rerun()
        if st.button(T("🏳️ Đầu hàng", "🏳️ Resign"), use_container_width=True):
            st.session_state.over = True
            st.session_state.winner = "Đen" if st.session_state.turn else "Đỏ"
            st.session_state.settings = False
            st.rerun()

b = st.session_state.board
if not st.session_state.over and not st.session_state.paused:
    st.caption(T("Chọn quân của mình, sau đó chọn ô đích.", "Select your piece, then its destination."))

    legal_moves = legal(b, st.session_state.turn)
    selected = st.session_state.selected
    destinations = [(m[2], m[3]) for m in legal_moves if selected == (m[0], m[1])]

    for r in range(10):
        cols = st.columns(9, gap="small")
        for c in range(9):
            p = b[r][c]
            text = "　" if p == "." else SYMBOL[p]
            if selected == (r, c):
                text = f"🔴{text}"
            elif (r, c) in destinations:
                text = f"•{text}"
            style = "primary" if (r, c) in destinations or selected == (r, c) else "secondary"
            if cols[c].button(text, key=f"cell_{r}_{c}", use_container_width=True):
                if selected and (r, c) in destinations:
                    play((selected[0], selected[1], r, c))
                    st.rerun()
                elif p != "." and p.isupper() == st.session_state.turn:
                    st.session_state.selected = (r, c)
                    st.rerun()
                else:
                    st.session_state.selected = None
                    st.rerun()

controls = st.columns(4)
with controls[0]:
    if st.button(T("💡 Gợi ý", "💡 Hint"), use_container_width=True, disabled=st.session_state.over or st.session_state.paused):
        moves = legal(b, st.session_state.turn)
        if moves:
            if st.session_state.turn:
                _, m = search(b, 2, -1000000, 1000000, True)
            else:
                _, m = search(b, 2, -1000000, 1000000, False)
            st.session_state.hint = m or random.choice(moves)
        st.rerun()
with controls[1]:
    if st.button(T("↩ Quay lại", "↩ Undo"), use_container_width=True, disabled=not st.session_state.snapshots):
        snap = st.session_state.snapshots.pop()
        st.session_state.board = snap["board"]
        st.session_state.turn = snap["turn"]
        st.session_state.history = snap["history"]
        st.session_state.over = snap["over"]
        st.session_state.winner = snap["winner"]
        # Khi đấu máy, hoàn tác thêm nước của bot nếu cần
        if st.session_state.mode == "bot" and st.session_state.snapshots:
            if st.session_state.turn is False:
                snap = st.session_state.snapshots.pop()
                st.session_state.board = snap["board"]
                st.session_state.turn = snap["turn"]
                st.session_state.history = snap["history"]
        st.rerun()
with controls[2]:
    if st.button(T("🔄 Chơi lại", "🔄 New Game"), use_container_width=True):
        fresh_game(st.session_state.mode, st.session_state.level)
        st.rerun()
with controls[3]:
    if st.button(T("🏳️ Đầu hàng", "🏳️ Resign"), use_container_width=True, disabled=st.session_state.over):
        st.session_state.over = True
        st.session_state.winner = "Đen" if st.session_state.turn else "Đỏ"
        st.rerun()

if st.session_state.hint:
    m = st.session_state.hint
    st.info(T(f"Gợi ý: từ hàng {m[0]+1}, cột {m[1]+1} đến hàng {m[2]+1}, cột {m[3]+1}",
              f"Hint: row {m[0]+1}, column {m[1]+1} to row {m[2]+1}, column {m[3]+1}"))

with st.expander(T("📜 Lịch sử nước đi", "📜 Move history"), expanded=True):
    if st.session_state.history:
        for i, move in enumerate(st.session_state.history, 1):
            st.write(f"{i}. {move}")
    else:
        st.caption(T("Chưa có nước đi.", "No moves yet."))

with st.expander(T("📖 Hướng dẫn luật cơ bản", "📖 Basic rules")):
    st.write(T(
        "Xe đi ngang/dọc; Pháo ăn qua một quân chắn; Mã đi chữ L nhưng có thể bị cản chân; "
        "Tượng đi chéo 2 ô và không qua sông; Sĩ đi chéo 1 ô trong cung; Tướng đi 1 ô trong cung; "
        "Tốt đi thẳng và sau khi qua sông có thể đi ngang.",
        "Rook moves straight; Cannon captures over one screen; Horse moves in an L but can be blocked; "
        "Elephant moves diagonally two squares and cannot cross the river; Advisor moves diagonally in the palace; "
        "King moves one step in the palace; Pawn moves forward and sideways after crossing the river."
    ))

with st.expander(T("📊 Thống kê phiên hiện tại", "📊 Session statistics")):
    st.write(T("Số nước đi", "Moves"), len(st.session_state.history))
    st.write(T("Chế độ", "Mode"), st.session_state.mode)
    st.write(T("Độ khó", "Difficulty"), st.session_state.level)
    st.download_button(
        T("💾 Tải lịch sử ván đấu", "💾 Download game history"),
        data=json.dumps({"moves": st.session_state.history}, ensure_ascii=False, indent=2),
        file_name="lich_su_co_tuong.json",
        mime="application/json"
    )
