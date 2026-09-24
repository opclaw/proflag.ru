#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Клиентская PDF-презентация аудита proflag.ru.

Принципы сборки (по согласованию с заказчиком):
  * 16:9, белый фон, 13 слайдов;
  * контент — «что нашли, чем это грозит, что даём в результате»:
    без технической кухни (robots.txt, куски кода, состав ТЗ, точные частоты
    и посадочные URL в клиентский PDF не попадают);
  * без цифр-обещаний: прогноза трафика/заявок в PDF нет. Вместо него —
    зафиксированная база, точки контроля и формат отчётности (слайд 11).
    Числовые ориентиры считаются отдельно и передаются приложением после
    этапа 1, когда база уточнена; в договоре KPI-цифрами не фиксируются.
    Причина: измеримое обещание результата = заверение об обстоятельствах
    (ст. 431.2 ГК РФ) и риск претензий при недостижении;
  * PDF «плоский»: страницы собираются из растра (нет текстового слоя —
    выделить/скопировать/отредактировать текст в нём нельзя) и дополнительно
    закрываются паролем владельца с запретом модификации и копирования.

Запуск:      python3 client-pdf/build.py
Результат:   client-pdf/PROFLAG-audit-klientu.pdf  +  client-pdf/slides/*.png
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
PNG_DIR = os.path.join(HERE, "slides")
PDF_OUT = os.path.join(HERE, "PROFLAG-audit-klientu.pdf")

W, H = 2400, 1350            # 16:9 → страница 13,33 × 7,5 in при 180 dpi
SS = 2                       # суперсэмплинг (рисуем в 2×, сжимаем LANCZOS)
M = 130                      # поле слайда
CW = W - 2 * M
PAGE_W_PT, PAGE_H_PT = 960.0, 540.0

OWNER_PW = "Proflag-2026-SmartSolutions"   # пароль владельца (для снятия защиты)

# ------------------------------------------------------------------ палитра
WHITE = (255, 255, 255)
INK = (13, 27, 42)
BODY = (72, 90, 112)
MUTED = (142, 158, 178)
LINE = (227, 233, 242)
PANEL = (247, 249, 252)
PANEL2 = (238, 243, 249)
BLUE = (44, 95, 168)
BLUE_MID = (110, 155, 212)
BLUE_SOFT = (232, 240, 250)
RED = (207, 56, 74)
RED_SOFT = (252, 235, 237)
GREEN = (23, 138, 92)
GREEN_SOFT = (231, 246, 239)
AMBER = (196, 134, 18)
AMBER_SOFT = (253, 244, 226)

FONT_FILES = {
    "400": "GolosText_400Regular.ttf",
    "500": "GolosText_500Medium.ttf",
    "600": "GolosText_600SemiBold.ttf",
    "700": "GolosText_700Bold.ttf",
    "800": "GolosText_800ExtraBold.ttf",
    "900": "GolosText_900Black.ttf",
}

_fcache = {}


def F(size, weight="600"):
    key = (int(round(size * SS)), weight)
    if key not in _fcache:
        _fcache[key] = ImageFont.truetype(os.path.join(FONTS, FONT_FILES[weight]), key[0])
    return _fcache[key]


def wrap_lines(text, maxw, size, weight="600"):
    """Перенос по словам (дизайн-единицы)."""
    f = F(size, weight)
    out = []
    for block in str(text).split("\n"):
        cur = ""
        for wd in block.split():
            t = (cur + " " + wd).strip()
            if f.getlength(t) / SS <= maxw or not cur:
                cur = t
            else:
                out.append(cur)
                cur = wd
        out.append(cur)
    return out


# ------------------------------------------------------------------ холст
class Slide:
    def __init__(self):
        self.img = Image.new("RGB", (W * SS, H * SS), WHITE)
        self.d = ImageDraw.Draw(self.img)

    # --- геометрия ---
    def _p(self, x, y):
        return (x * SS, y * SS)

    def _b(self, box):
        return (box[0] * SS, box[1] * SS, box[2] * SS, box[3] * SS)

    # --- примитивы ---
    def rect(self, box, fill=None, outline=None, width=1):
        self.d.rectangle(self._b(box), fill=fill, outline=outline, width=max(1, round(width * SS)))

    def rrect(self, box, r=16, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self._b(box), radius=round(r * SS), fill=fill, outline=outline,
                                 width=max(1, round(width * SS)))

    def line(self, p1, p2, fill=LINE, width=2):
        self.d.line([self._p(*p1), self._p(*p2)], fill=fill, width=max(1, round(width * SS)))

    def circle(self, cx, cy, r, fill=None, outline=None, width=1):
        self.d.ellipse(self._b((cx - r, cy - r, cx + r, cy + r)), fill=fill, outline=outline,
                       width=max(1, round(width * SS)))

    def poly(self, pts, fill):
        self.d.polygon([self._p(*p) for p in pts], fill=fill)

    # --- текст ---
    def tw(self, s, size, weight="600", ls=0):
        wpx = F(size, weight).getlength(s)
        if ls:
            wpx += ls * SS * max(0, len(s) - 1)
        return wpx / SS

    def text(self, x, y, s, size=28, weight="600", color=INK, anchor="la", ls=0):
        f = F(size, weight)
        total = self.tw(s, size, weight, ls)
        if ls:
            if anchor.startswith("m"):
                x -= total / 2
            elif anchor.startswith("r"):
                x -= total
            cx = x
            for ch in s:
                self.d.text(self._p(cx, y), ch, font=f, fill=color, anchor="la")
                cx += f.getlength(ch) / SS + ls
        else:
            self.d.text(self._p(x, y), s, font=f, fill=color, anchor=anchor)
        return total

    def para(self, x, y, text, size=27, weight="500", color=BODY, maxw=None, lh=1.42, align="l"):
        maxw = maxw if maxw is not None else (W - M - x)
        yy = y
        for ln in wrap_lines(text, maxw, size, weight):
            if align == "c":
                self.text(x + maxw / 2, yy, ln, size, weight, color, anchor="ma")
            elif align == "r":
                self.text(x + maxw, yy, ln, size, weight, color, anchor="ra")
            else:
                self.text(x, yy, ln, size, weight, color)
            yy += size * lh
        return yy

    # --- компоненты ---
    def flagmark(self, x, y, h=26):
        """Мини-флаг (логотип презентации)."""
        w = h * 1.42
        pole_w = max(2.0, h * 0.11)
        self.rrect((x, y - h * 0.08, x + pole_w, y + h * 1.25), r=pole_w / 2, fill=(178, 192, 210))
        fx = x + pole_w * 2.1
        st = h / 3
        self.rect((fx, y, fx + w, y + st), fill=(226, 233, 241))
        self.rect((fx, y + st, fx + w, y + 2 * st), fill=BLUE)
        self.rect((fx, y + 2 * st, fx + w, y + h), fill=RED)
        return fx + w

    def chrome(self, page, total, title_short=None):
        fx = self.flagmark(M, 70, 26)
        self.text(fx + 20, 74, "PROFLAG · АУДИТ САЙТА", 21, "700", MUTED, ls=3.4)
        self.text(W - M, 74, "22 СЕНТЯБРЯ 2026", 21, "600", MUTED, anchor="ra", ls=2.2)
        self.line((M, 1234), (W - M, 1234), LINE, 2)
        self.text(M, 1256, "Конфиденциально · подготовлено для ООО «Профлаг»", 20, "500", MUTED)
        self.text(W - M, 1256, "%02d / %02d" % (page, total), 20, "700", MUTED, anchor="ra", ls=1.5)

    def head(self, title, lead=None, accent=None, y=146, size=62):
        if accent:
            w = self.text(M, y, title, size, "800", INK)
            self.text(M + w + 18, y + 6, accent, size - 6, "700", MUTED)
        else:
            self.text(M, y, title, size, "800", INK)
        top = y + size * 1.34
        if lead:
            top = self.para(M, top + 6, lead, 28, "500", BODY, maxw=1720, lh=1.44)
        return top + 40

    def label(self, x, y, text, color=MUTED, size=21, dash=34):
        self.rect((x, y + size * 0.42, x + dash, y + size * 0.42 + 3), fill=color)
        self.text(x + dash + 14, y, text, size, "700", color, ls=3.0)
        return x + dash + 14 + self.tw(text, size, "700", ls=3.0)

    def pill(self, x, y, text, fg, bg, size=22, weight="700", padx=20, pady=11, r=999, outline=None):
        w = self.tw(text, size, weight) + padx * 2
        h = size * 1.34 + pady * 2
        self.rrect((x, y, x + w, y + h), r=min(r, h / 2), fill=bg, outline=outline, width=2)
        self.text(x + padx, y + pady, text, size, weight, fg)
        return w, h

    def mark_cross(self, cx, cy, r=15, color=RED):
        self.circle(cx, cy, r, fill=color)
        k = r * 0.46
        self.line((cx - k, cy - k), (cx + k, cy + k), WHITE, max(2, r * 0.24))
        self.line((cx - k, cy + k), (cx + k, cy - k), WHITE, max(2, r * 0.24))

    def mark_check(self, cx, cy, r=15, color=GREEN):
        self.circle(cx, cy, r, fill=color)
        w = max(2, r * 0.24)
        self.line((cx - r * 0.44, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), WHITE, w)
        self.line((cx - r * 0.1, cy + r * 0.38), (cx + r * 0.48, cy - r * 0.36), WHITE, w)

    def mark_num(self, cx, cy, n, r=26, color=BLUE, bg=BLUE_SOFT, size=27):
        self.circle(cx, cy, r, fill=bg)
        self.text(cx, cy - size * 0.68, str(n), size, "800", color, anchor="ma")

    def hbar(self, x, y, w, h, pct, color, track=PANEL2, r=None):
        r = r if r is not None else h / 2
        self.rrect((x, y, x + w, y + h), r=r, fill=track)
        fw = max(h, w * pct)
        self.rrect((x, y, x + fw, y + h), r=r, fill=color)
        return fw

    def bullet(self, x, y, head_txt, body_txt, maxw, mark=None, mark_color=BLUE,
               hs=28, bs=25, lh=1.4, gap=26, indent=52):
        if mark == "cross":
            self.mark_cross(x + 15, y + hs * 0.52, 15, mark_color)
        elif mark == "check":
            self.mark_check(x + 15, y + hs * 0.52, 15, mark_color)
        elif mark == "dot":
            self.circle(x + 15, y + hs * 0.5, 6, fill=mark_color)
        tx = x + indent
        yy = y
        if head_txt:
            self.text(tx, yy, head_txt, hs, "700", INK)
            yy += hs * 1.36
        if body_txt:
            yy = self.para(tx, yy, body_txt, bs, "500", BODY, maxw=maxw - indent, lh=lh)
        return yy + gap

    def save(self, path):
        out = self.img.resize((W, H), Image.LANCZOS)
        out.save(path, "PNG", optimize=True)
        return path

    def paste(self, box, img, r=0):
        x, y = int(box[0] * SS), int(box[1] * SS)
        if r:
            mask = Image.new("L", img.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.size[0] - 1, img.size[1] - 1),
                                                   radius=int(r * SS), fill=255)
            self.img.paste(img, (x, y), mask)
        else:
            self.img.paste(img, (x, y))


def region(w, h, bg=WHITE):
    return Image.new("RGB", (int(w * SS), int(h * SS)), bg)


def waved_flag(box, r=22, amp=26, waves=1.35, phase=0.0, colors=None):
    """Декоративный «развевающийся» триколор внутри скруглённой плашки."""
    x0, y0, x1, y1 = box
    w, h = int((x1 - x0) * SS), int((y1 - y0) * SS)
    img = Image.new("RGB", (w, h), (243, 246, 250))
    dd = ImageDraw.Draw(img)
    colors = colors or [(232, 238, 246), (60, 111, 181), (214, 84, 99)]
    n = len(colors)
    sh = h / n
    steps = 220
    for i, c in enumerate(colors):
        top, bot = [], []
        for k in range(steps + 1):
            t = k / steps
            x = w * t
            off = amp * SS * math.sin(t * math.pi * 2 * waves + phase + i * 0.28)
            off *= 0.55 + 0.45 * math.sin(t * math.pi)
            top.append((x, i * sh + off))
            bot.append((x, (i + 1) * sh + off))
        dd.polygon(top + bot[::-1], fill=c)
    return img, r


# ================================================================== СЛАЙДЫ
def s01(s, page, total):
    # декоративная волна-триколор по нижнему краю
    img, r = waved_flag((0, 1294, W, 1350), r=0, amp=14, waves=3.2, phase=0.4,
                        colors=[(233, 239, 247), (96, 143, 202), (222, 122, 133)])
    s.paste((0, 1294, W, 1350), img)

    s.label(M, 150, "АУДИТ САЙТА · SEO · МАРКЕТИНГ · КОНВЕРСИЯ", BLUE, 23, dash=46)

    s.text(M, 214, "Аудит сайта", 54, "700", MUTED)
    x = M
    x += s.text(x, 274, "proflag", 148, "900", INK)
    s.text(x, 274, ".ru", 148, "900", BLUE)

    s.text(M, 470, "Диагностика продаж и план роста на 90 дней", 46, "800", BLUE)

    s.para(M, 570,
           "Производство работает 21 год, клиенты его любят. При этом сайт уводит заявки "
           "к конкурентам — по измеримым и устранимым причинам.\n"
           "Ниже: что именно теряется, в каких цифрах это выражается и что мы предлагаем сделать.",
           30, "500", BODY, maxw=1180, lh=1.5)

    s.text(M, 776,
           "Диагностика и план работ, а не обещание результата: оценки — по открытым данным на 22.09.2026.",
           21, "500", MUTED)

    # плитки фактов
    tiles = [
        ("21 год", "на рынке, своё производство"),
        ("75 000", "изделий в месяц"),
        ("5 часов", "тираж после согласования"),
        ("5 блоков", "потерь найдено в аудите"),
    ]
    tw_ = 292
    for i, (v, d) in enumerate(tiles):
        x0 = M + i * (tw_ + 20)
        s.rrect((x0, 838, x0 + tw_, 838 + 176), r=18, fill=PANEL, outline=LINE, width=2)
        s.rect((x0 + 30, 878, x0 + 30 + 44, 878 + 5), fill=BLUE)
        s.text(x0 + 30, 900, v, 46, "900", INK)
        s.para(x0 + 30, 962, d, 21, "500", MUTED, maxw=tw_ - 60, lh=1.34)

    # правая панель: диагностика индекса
    px0, py0, px1, py1 = 1470, 214, W - M, 1014
    s.rrect((px0, py0, px1, py1), r=26, fill=PANEL, outline=LINE, width=2)
    s.label(px0 + 48, py0 + 52, "СТРАНИЦ В ПОИСКЕ ЯНДЕКСА", MUTED, 21)

    s.text(px0 + 48, py0 + 104, "290", 150, "900", INK)
    s.pill(px0 + 400, py0 + 176, "−64 за месяц", RED, RED_SOFT, 25, "800")
    s.text(px0 + 48, py0 + 286, "proflag.ru — индекс тает", 26, "600", BODY)

    s.hbar(px0 + 48, py0 + 348, px1 - px0 - 96, 20, 290 / 1385, RED, track=(232, 236, 243))

    s.line((px0 + 48, py0 + 424), (px1 - 48, py0 + 424), LINE, 2)

    s.text(px0 + 48, py0 + 462, "1 385", 150, "900", BLUE)
    s.pill(px0 + 470, py0 + 534, "+31 за месяц", GREEN, GREEN_SOFT, 25, "800")
    s.text(px0 + 48, py0 + 644, "лидер ниши megaflag.ru — растёт", 26, "600", BODY)
    s.hbar(px0 + 48, py0 + 686, px1 - px0 - 96, 20, 1.0, BLUE, track=(232, 236, 243))

    s.para(px0 + 48, py0 + 724,
           "Разрыв в 4,8 раза по числу точек входа в выдачу — при том, что производство у вас сильнее.",
           23, "600", BODY, maxw=px1 - px0 - 96, lh=1.4)

    # футер титула
    s.line((M, 1180), (W - M, 1180), LINE, 2)
    s.text(M, 1210, "Подготовлено для ООО «Профлаг» · конфиденциально", 23, "600", BODY)
    s.text(M, 1250, "Дата аудита: 22 сентября 2026 · Москва", 21, "500", MUTED)
    s.text(W - M, 1210, "Smart Solutions · smartsolutions.today", 23, "700", INK, anchor="ra")
    s.text(W - M, 1250, "+7 925 090-95-00 · звонок, WhatsApp, Telegram", 21, "600", BLUE, anchor="ra")


def s02(s, page, total):
    s.chrome(page, total)
    top = s.head("Диагноз за 30 секунд",
                 "Сильное производство — слабый сайт. Проблема не в «плохих продажах» вообще, "
                 "а в трёх конкретных вещах, которые видны в цифрах.")
    cards = [
        ("01", "Техническое SEO устарело",
         "Страницы тяжёлые и отдаются медленно, настройки индексации противоречат сами себе. "
         "Яндекс месяц за месяцем выкидывает страницы из поиска: минус 64 за последний месяц.",
         RED, RED_SOFT),
        ("02", "Сайт не отвечает на вопрос покупателя",
         "Человек ищет «флаг 90×135, цена, в наличии». Сайт предлагает «оставьте заявку — "
         "рассчитаем за 15 минут». До расчёта клиент просто не доходит: он звонит тому, у кого цена на экране.",
         AMBER, AMBER_SOFT),
        ("03", "Доверие не подтверждено",
         "Нет реквизитов юрлица, домен оформлен на частное лицо, нет разметки для сниппетов и соцсетей, "
         "один раздел главного меню сломан. Клиент с чеком 300 000 ₽ проверяет сайт до звонка.",
         BLUE, BLUE_SOFT),
    ]
    cw = (CW - 2 * 44) / 3
    y0 = 392
    for i, (num, title, body, col, soft) in enumerate(cards):
        x0 = M + i * (cw + 44)
        s.rrect((x0, y0, x0 + cw, y0 + 556), r=22, fill=WHITE, outline=LINE, width=2)
        s.rrect((x0, y0, x0 + cw, y0 + 12), r=6, fill=col)
        s.rrect((x0 + 44, y0 + 58, x0 + 44 + 118, y0 + 58 + 74), r=16, fill=soft)
        s.text(x0 + 103, y0 + 74, num, 40, "900", col, anchor="ma")
        s.para(x0 + 44, y0 + 176, title, 36, "800", INK, maxw=cw - 88, lh=1.24)
        s.para(x0 + 44, y0 + 300, body, 26, "500", BODY, maxw=cw - 88, lh=1.48)

    y1 = 996
    s.rrect((M, y1, W - M, y1 + 168), r=22, fill=(244, 248, 253), outline=(214, 226, 242), width=2)
    s.rect((M, y1 + 20, M + 8, y1 + 148), fill=BLUE)
    s.text(M + 56, y1 + 40, "Вывод", 24, "800", BLUE, ls=2.4)
    s.para(M + 56, y1 + 80,
           "Сайт отдаёт клиентов конкурентам ещё до того, как они увидят ваше производство. "
           "Все три причины устранимы за 90 дней — поэтапно и с измеримым результатом.",
           29, "600", INK, maxw=CW - 120, lh=1.42)


def s03(s, page, total):
    s.chrome(page, total)
    top = s.head("Где именно проигрыш",
                 "Сравнение с лидером ниши megaflag.ru по открытым измеримым факторам. "
                 "Источники: be1.ru, живые страницы сайтов, выдача Яндекса — 22.09.2026.",
                 accent="proflag.ru против лидера ниши")

    c1, c2, c3, c4 = 880, 430, 400, 430
    x1, x2, x3 = M + c1, M + c1 + c2, M + c1 + c2 + c3
    y = 404
    s.rrect((M, y, W - M, y + 62), r=14, fill=PANEL2)
    for x, t in ((M + 34, "ФАКТОР"), (x1 + 24, "PROFLAG.RU"), (x2 + 24, "ЛИДЕР НИШИ"), (x3 + 24, "ЧТО ЭТО ЗНАЧИТ")):
        s.text(x, y + 18, t, 21, "800", MUTED, ls=2.6)

    rows = [
        ("Страниц в индексе Яндекса", "290", "−64/мес", "1 385", "+31/мес", "×4,8 меньше точек входа", RED),
        ("ИКС Яндекса (качество домена)", "270", "", "360", "", "домен оценивается ниже", RED),
        ("Вес главной страницы", "358 КБ", "", "72 КБ", "", "в 5 раз тяжелее", RED),
        ("Время отклика сайта", "~3 с", "", "~0,8 с", "", "в 4 раза медленнее", RED),
        ("Цена и наличие в карточке товара", "нет", "", "есть", "", "в розничной выдаче вас не будет", RED),
        ("Онлайн-расчёт стоимости", "нет", "", "есть", "", "заявка только через форму", RED),
        ("Разметка товара и соцсетей", "нет", "", "есть", "", "сниппет без цены и картинки", RED),
        ("Рабочие разделы меню", "1 сломан", "", "—", "", "клик по меню уходит в ошибку", RED),
    ]
    y += 62
    rh = 82
    for i, (f, v1, n1, v2, n2, verdict, col) in enumerate(rows):
        yy = y + i * rh
        if i % 2 == 1:
            s.rect((M, yy, W - M, yy + rh), fill=(251, 252, 254))
        s.line((M, yy + rh), (W - M, yy + rh), (238, 242, 248), 2)
        cy = yy + rh / 2
        s.text(M + 34, cy - 15, f, 27, "600", INK)
        s.text(x1 + 24, cy - 18, v1, 30, "800", RED)
        if n1:
            s.text(x1 + 24 + s.tw(v1, 30, "800") + 14, cy - 12, n1, 22, "700", RED)
        s.text(x2 + 24, cy - 18, v2, 30, "800", (60, 78, 100))
        if n2:
            s.text(x2 + 24 + s.tw(v2, 30, "800") + 14, cy - 12, n2, 22, "700", GREEN)
        s.pill(x3 + 24, cy - 21, verdict, col, RED_SOFT, 21, "700")
    s.para(M, y + len(rows) * rh + 34,
           "Единственная строка, где вы впереди, — возраст домена: 21 год против 17 у лидера. "
           "Всё остальное отыгрывается работой, а не временем.",
           26, "600", BODY, maxw=CW, lh=1.42)


def browser_mock(s, box, url, title, sub, host):
    x0, y0, x1, y1 = box
    s.rrect(box, r=18, fill=PANEL, outline=LINE, width=2)
    s.rect((x0 + 2, y0 + 34, x1 - 2, y0 + 60), fill=PANEL)
    s.line((x0, y0 + 60), (x1, y0 + 60), LINE, 2)
    for i, c in enumerate([(224, 122, 133), (233, 190, 110), (140, 196, 150)]):
        s.circle(x0 + 34 + i * 30, y0 + 30, 8, fill=c)
    s.rrect((x0 + 130, y0 + 14, x0 + 130 + 330, y0 + 46), r=16, fill=WHITE)
    s.text(x0 + 150, y0 + 21, url, 19, "600", MUTED)

    cx = (x0 + x1) / 2
    s.circle(cx, y0 + 106, 30, fill=RED_SOFT)
    s.rect((cx - 4, y0 + 88, cx + 4, y0 + 114), fill=RED)
    s.circle(cx, y0 + 124, 5, fill=RED)
    s.text(cx, y0 + 148, title, 30, "800", RED, anchor="ma")
    s.text(cx, y0 + 194, sub, 22, "500", BODY, anchor="ma")
    s.text(cx, y0 + 226, host, 20, "600", MUTED, anchor="ma")


def photo_tile(s, box):
    x0, y0, x1, y1 = box
    s.rrect(box, r=12, fill=PANEL2, outline=(222, 229, 238), width=2)
    w, h = x1 - x0, y1 - y0
    bx, by = x0 + w * 0.22, y0 + h * 0.68
    s.poly([(bx, by), (bx + w * 0.22, by - h * 0.26), (bx + w * 0.44, by)], fill=(200, 211, 224))
    s.poly([(bx + w * 0.3, by), (bx + w * 0.5, by - h * 0.36), (bx + w * 0.72, by)], fill=(182, 196, 213))
    s.circle(x0 + w * 0.72, y0 + h * 0.3, h * 0.09, fill=(206, 216, 228))


def s04(s, page, total):
    s.chrome(page, total)
    s.head("Две потери, которые видны сразу",
           "Их находят за минуту, а стоят они заявок каждый день. Обе закрываются в первые дни работ.")

    y0, hh = 392, 676
    cw = (CW - 60) / 2

    # --- карточка 1: сломанный раздел меню
    x0 = M
    s.rrect((x0, y0, x0 + cw, y0 + hh), r=22, fill=WHITE, outline=LINE, width=2)
    s.pill(x0 + 48, y0 + 44, "ПОТЕРЯ 1 · КЛИКИ УХОДЯТ В ОШИБКУ", RED, RED_SOFT, 20, "800")
    s.para(x0 + 48, y0 + 116, "Пункт главного меню ведёт в никуда", 36, "800", INK, maxw=cw - 96, lh=1.24)
    browser_mock(s, (x0 + 48, y0 + 210, x0 + cw - 48, y0 + 462),
                 "print.proflag.ru", "Сайт размещён некорректно",
                 "Раздел «Печать на ткани» из главного меню", "server14.hosting.reg.ru")
    s.para(x0 + 48, y0 + 500,
           "Посетитель кликает по услуге в меню и видит ошибку хостинга вместо предложения. "
           "Спрос по направлению «печать на ткани» в Москве и области — тысячи обращений в месяц "
           "(оценка по открытым сервисам): сейчас этот поток обрывается.",
           25, "500", BODY, maxw=cw - 96, lh=1.46)

    # --- карточка 2: фото закрыты от поиска
    x1 = M + cw + 60
    s.rrect((x1, y0, x1 + cw, y0 + hh), r=22, fill=WHITE, outline=LINE, width=2)
    s.pill(x1 + 48, y0 + 44, "ПОТЕРЯ 2 · ФОТО НЕ ВИДНО В ПОИСКЕ", RED, RED_SOFT, 20, "800")
    s.para(x1 + 48, y0 + 116, "Все фотографии продукции закрыты от роботов", 36, "800", INK, maxw=cw - 96, lh=1.24)
    gx, gy = x1 + 48, y0 + 210
    gw = (cw - 96 - 2 * 24) / 3
    gh = 110
    for r_ in range(2):
        for c_ in range(3):
            bx = gx + c_ * (gw + 24)
            by = gy + r_ * (gh + 22)
            photo_tile(s, (bx, by, bx + gw, by + gh))
            s.mark_cross(bx + gw - 16, by + 16, 15, RED)
    s.text(gx, gy + 2 * gh + 44, "Яндекс.Картинки и Google Images: 0 ваших фотографий", 23, "700", RED)
    s.para(x1 + 48, y0 + 528,
           "Флаг — визуальный товар, его выбирают глазами. Настройки сайта закрывают все изображения "
           "от поисковых роботов, поэтому весь трафик из поиска по картинкам забирают конкуренты.",
           25, "500", BODY, maxw=cw - 96, lh=1.46)

    # --- нижняя полоса
    yb = 1104
    s.rrect((M, yb, W - M, yb + 104), r=18, fill=(244, 248, 253), outline=(214, 226, 242), width=2)
    bolt = [(0, 0), (16, 0), (7, 15), (20, 15), (2, 40), (8, 20), (-3, 20)]
    s.poly([(M + 56 + bx * 1.05, yb + 30 + by * 1.05) for bx, by in bolt], BLUE)
    s.text(M + 110, yb + 32,
           "Обе потери закрываются на старте работ — это первое, что мы делаем.",
           28, "700", INK)


def s05(s, page, total):
    s.chrome(page, total)
    s.head("Индекс Яндекса тает",
           "Поисковик месяц за месяцем убирает ваши страницы из выдачи — то есть сокращает число "
           "поводов показать вас клиенту.")

    y0, hh = 392, 748
    lw = 780
    s.rrect((M, y0, M + lw, y0 + hh), r=22, fill=PANEL, outline=LINE, width=2)
    s.label(M + 48, y0 + 52, "ЯНДЕКС", MUTED, 21)
    s.text(M + 48, y0 + 92, "290", 168, "900", INK)
    s.pill(M + 48, y0 + 300, "−64 за месяц", RED, RED_SOFT, 26, "800")
    s.text(M + 300, y0 + 310, "страниц выпадает", 24, "600", BODY)
    s.hbar(M + 48, y0 + 392, lw - 96, 18, 290 / 1385, RED, track=(229, 234, 241))
    s.text(M + 48, y0 + 424, "доля от лидера ниши — 21%", 22, "600", MUTED)

    s.line((M + 48, y0 + 492), (M + lw - 48, y0 + 492), LINE, 2)
    s.label(M + 48, y0 + 524, "GOOGLE", MUTED, 21)
    s.text(M + 48, y0 + 564, "249", 96, "900", INK)
    s.pill(M + 250, y0 + 600, "+80", GREEN, GREEN_SOFT, 24, "800")
    s.para(M + 48, y0 + 664, "Яндекс уже пессимизирует сайт, Google — пока нет. "
                            "Окно, в котором можно догнать, закрывается.",
           22, "600", BODY, maxw=lw - 96, lh=1.4)

    rx = M + lw + 60
    rw = W - M - rx
    s.rrect((rx, y0, W - M, y0 + hh), r=22, fill=WHITE, outline=LINE, width=2)
    s.para(rx + 48, y0 + 48, "Что стоит за падением", 36, "800", INK, maxw=rw - 96, lh=1.24)
    yy = y0 + 136
    items = [
        ("Шаблонные тексты примерно на 100 категориях",
         "Одинаковые блоки «преимущества заказа» и описания, собранные по одному шаблону. "
         "Яндекс склеивает такие страницы и понижает сайт за переспам."),
        ("«Тонкие» страницы портфолио — около 130",
         "Одна-две фразы и фотография: роботу нечего индексировать, а бюджет обхода расходуется впустую."),
        ("Часть фотографий в работах не открывается",
         "Кейсы, которые должны продавать, выглядят сломанными — и для клиента, и для робота."),
        ("Сезонные страницы не обновляются",
         "9 Мая, выборы, Новый год отработали и «умерли» в индексе до следующего года."),
    ]
    for h_, b_ in items:
        yy = s.bullet(rx + 48, yy, h_, b_, rw - 96, mark="cross", hs=28, bs=24, gap=22, indent=52)

    yy += 6
    s.rrect((rx + 48, yy, W - M - 48, yy + 76), r=16, fill=RED_SOFT)
    s.text(rx + 80, yy + 24, "Пока причины не закрыты, динамика сохраняется: за последний месяц — минус 64 страницы.", 25, "800", RED)


def s06(s, page, total):
    s.chrome(page, total)
    s.head("Нет цены на экране — нет покупки",
           "Так выглядит выдача по одному из самых частых коммерческих запросов ниши. "
           "Вашего сайта в ней нет — и это не вопрос позиций.")

    y0, hh = 392, 796
    lw = 1200
    s.rrect((M, y0, M + lw, y0 + hh), r=22, fill=WHITE, outline=LINE, width=2)
    s.pill(M + 48, y0 + 44, "ВЫДАЧА ЯНДЕКСА · МОСКВА", BLUE, BLUE_SOFT, 20, "800")
    s.rrect((M + 48, y0 + 112, M + lw - 48, y0 + 190), r=16, fill=PANEL, outline=LINE, width=2)
    s.text(M + 78, y0 + 136, "флаг россии купить", 30, "700", INK)
    bx = M + lw - 48 - 150
    s.rrect((bx, y0 + 124, bx + 132, y0 + 178), r=14, fill=BLUE)
    s.text(bx + 66, y0 + 138, "Найти", 24, "700", WHITE, anchor="ma")

    rows = [
        ("kanc-mir.ru", "Знамя Победы 90×135, флажок на древке", "291 ₽", "6 429 шт в наличии", False),
        ("garsingshop.ru", "Флаг России 90×135 см, полиэфир", "770 ₽", "в наличии, доставка", False),
        ("sp-snab.ru", "Флаг РФ 90×135, стандарт", "900 ₽", "купить в 1 клик", False),
        ("proflag.ru", "«Оставьте заявку — рассчитаем за 15 минут»", "цены нет", "только форма и звонок", True),
    ]
    ry = y0 + 224
    rh = 118
    for i, (dom, ttl, price, note, you) in enumerate(rows):
        yy = ry + i * rh
        if you:
            s.rrect((M + 40, yy + 6, M + lw - 40, yy + rh - 10), r=16, fill=RED_SOFT)
            s.mark_cross(M + 82, yy + rh / 2 - 2, 17, RED)
        else:
            s.line((M + 48, yy + rh - 6), (M + lw - 48, yy + rh - 6), (240, 243, 248), 2)
            s.rrect((M + 66, yy + 24, M + 122, yy + 80), r=12, fill=PANEL2)
            s.text(M + 94, yy + 38, dom[0].upper(), 26, "800", MUTED, anchor="ma")
        tx = M + 148 if not you else M + 122
        s.text(tx, yy + 22, dom, 22, "700", RED if you else MUTED, ls=0.6)
        s.text(tx, yy + 54, ttl, 27, "700" if not you else "600", INK if not you else RED)
        pw, ph = s.pill(M + lw - 88 - s.tw(price, 30, "900") - 44, yy + 24, price,
                        RED if you else GREEN, WHITE if you else GREEN_SOFT, 30, "900", padx=22, pady=10)
        s.text(M + lw - 70, yy + 86, note, 20, "600", RED if you else MUTED, anchor="ra")

    s.para(M + 48, ry + 4 * rh + 16,
           "Покупатель сравнивает цены за 10 секунд. Страницы с ценой и наличием у вас нет — "
           "значит, нет и шанса попасть в эту выдачу.",
           26, "600", BODY, maxw=lw - 96, lh=1.42)

    rx = M + lw + 60
    rw = W - M - rx
    s.rrect((rx, y0, W - M, y0 + hh), r=22, fill=PANEL, outline=LINE, width=2)
    s.para(rx + 44, y0 + 48, "Два разных спроса — один сценарий на сайте", 34, "800", INK, maxw=rw - 88, lh=1.26)

    blocks = [
        ("РОЗНИЦА", "«Купить готовый флаг»",
         "Нужны цена, наличие и отгрузка сегодня. Таких страниц нет — выдачу забирают магазины "
         "с ценой 291–900 ₽ и тысячами отзывов.", BLUE, BLUE_SOFT),
        ("B2B", "«Изготовить на заказ»",
         "Ваша сильная сторона: срочность и полный цикл. Но цену клиент не видит до звонка — "
         "и уходит туда, где стоимость считается на экране за секунды.", AMBER, AMBER_SOFT),
    ]
    by = y0 + 176
    for tag, ttl, body, col, soft in blocks:
        s.rrect((rx + 44, by, W - M - 44, by + 236), r=18, fill=WHITE, outline=LINE, width=2)
        s.pill(rx + 76, by + 26, tag, col, soft, 20, "800")
        s.text(rx + 76, by + 84, ttl, 30, "800", INK)
        s.para(rx + 76, by + 126, body, 24, "500", BODY, maxw=rw - 152, lh=1.44)
        by += 256

    s.rrect((rx + 44, y0 + 676, W - M - 44, y0 + 676 + 112), r=18, fill=(244, 248, 253))
    s.para(rx + 76, y0 + 700,
           "Решение — витрина готовых позиций и мгновенный расчёт стоимости. "
           "Как устроено — рабочий материал проекта.",
           22, "700", INK, maxw=rw - 152, lh=1.42)


def s07(s, page, total):
    s.chrome(page, total)
    s.head("Доверие: что видит клиент с чеком 300 000 ₽",
           "B2B-заказчик и тем более госструктура проверяют сайт до звонка. "
           "Слева — чего он не находит, справа — что у вас уже есть, но не работает.")

    y0, hh = 392, 676
    cw = (CW - 60) / 2
    cols = [
        (M, "Не подтверждено", RED, RED_SOFT, "cross", [
            ("Реквизиты юрлица", "ИНН, ОГРН и юридический адрес не указаны нигде на сайте"),
            ("Домен оформлен на частное лицо", "Для B2B и госзаказчика это красный флаг"),
            ("Нет разметки для сниппетов и соцсетей", "Репост в Telegram и VK выглядит «голым», без картинки"),
            ("Битые фотографии в портфолио", "Работы, которые должны продавать, не открываются"),
            ("Кнопка заказа ведёт на личный мобильный", "Размывает доверие и ломает аналитику звонков"),
            ("Мёртвые кнопки в футере", "Skype, «Мой Мир», Instagram и Facebook — вместо VK и Telegram"),
        ]),
        (M + cw + 60, "Есть, но не работает на вас", GREEN, GREEN_SOFT, "check", [
            ("Рейтинг 5,0 и свежие отзывы на Яндекс.Картах", "Клиенты хвалят менеджеров поимённо — на сайте отзывов нет"),
            ("Благодарности госструктур", "Префектура ЮАО Москвы, ГБУ, благотворительные фонды"),
            ("Кейсы федерального уровня", "Фрегат «Херсонес», академия «Спартак», ТРЦ «Метрополис», ЦСКА/УЕФА"),
            ("Сертификаты и условия возврата", "Страницы есть, но спрятаны глубоко в футере"),
            ("21 год производства, 75 000 изделий в месяц", "Об этом не сказано ни в одном заголовке сайта"),
        ]),
    ]
    for x0, ttl, col, soft, mark, items in cols:
        s.rrect((x0, y0, x0 + cw, y0 + hh), r=22, fill=WHITE, outline=LINE, width=2)
        s.rrect((x0, y0, x0 + cw, y0 + 12), r=6, fill=col)
        s.text(x0 + 48, y0 + 44, ttl, 34, "800", INK)
        yy = y0 + 128
        for h_, b_ in items:
            if mark == "cross":
                s.mark_cross(x0 + 63, yy + 14, 15, col)
            else:
                s.mark_check(x0 + 63, yy + 14, 15, col)
            s.text(x0 + 104, yy, h_, 27, "700", INK)
            s.text(x0 + 104, yy + 38, b_, 23, "500", BODY)
            yy += 90
    yb = 1104
    s.rrect((M, yb, W - M, yb + 104), r=18, fill=(244, 248, 253), outline=(214, 226, 242), width=2)
    s.rect((M, yb + 18, M + 8, yb + 86), fill=BLUE)
    s.para(M + 48, yb + 30,
           "Активы доверия у вас сильнее, чем у половины сайтов из топа выдачи. Сайт их просто не показывает — "
           "а это то, что мы включаем в работу первым.",
           28, "700", INK, maxw=CW - 110, lh=1.4)


def s08(s, page, total):
    s.chrome(page, total)
    s.head("Конкуренты выше не потому, что флаги лучше",
           "Ни одна строка сравнения не проигрывается качеством печати — только «упаковкой» сайта.")

    y0, hh = 392, 628
    lw = 1240
    s.rrect((M, y0, M + lw, y0 + hh), r=22, fill=WHITE, outline=LINE, width=2)
    s.text(M + 48, y0 + 44, "proflag.ru против лидера ниши", 32, "800", INK)
    s.rect((M + 48, y0 + 112, M + 76, y0 + 130), fill=RED)
    s.text(M + 90, y0 + 106, "PROFLAG.RU", 20, "800", MUTED, ls=2.2)
    s.rect((M + 330, y0 + 112, M + 358, y0 + 130), fill=BLUE)
    s.text(M + 372, y0 + 106, "MEGAFLAG.RU", 20, "800", MUTED, ls=2.2)
    s.text(M + lw - 48, y0 + 106, "данные be1.ru, 22.09.2026", 20, "500", MUTED, anchor="ra")

    metrics = [
        ("Страниц в индексе Яндекса", 290, 1385, "290", "1 385", "×4,8"),
        ("ИКС Яндекса", 270, 360, "270", "360", "−25%"),
        ("Вес главной страницы, КБ  ·  меньше = лучше", 358, 72, "358 КБ", "72 КБ", "×5"),
        ("Время отклика, секунды  ·  меньше = лучше", 3.0, 0.8, "~3 с", "~0,8 с", "×4"),
    ]
    bx = M + 48
    bw = lw - 96 - 330
    yy = y0 + 168
    for name, v1, v2, l1, l2, gap in metrics:
        mx = max(v1, v2)
        s.text(bx, yy, name, 24, "600", BODY)
        w1 = s.hbar(bx, yy + 40, bw, 20, v1 / mx, RED)
        s.text(bx + w1 + 16, yy + 34, l1, 24, "800", RED)
        w2 = s.hbar(bx, yy + 72, bw, 20, v2 / mx, BLUE)
        s.text(bx + w2 + 16, yy + 66, l2, 24, "800", BLUE)
        s.pill(M + lw - 48 - 118, yy + 40, gap, RED, RED_SOFT, 22, "800", padx=18, pady=8)
        yy += 116

    rx = M + lw + 60
    rw = W - M - rx
    s.rrect((rx, y0, W - M, y0 + hh), r=22, fill=PANEL, outline=LINE, width=2)
    s.para(rx + 44, y0 + 44, "Чем они берут", 32, "800", INK, maxw=rw - 88, lh=1.24)
    yy = y0 + 132
    for h_, b_ in [
        ("Цена и наличие на карточке товара", "видно сразу, без звонка и заявки"),
        ("Онлайн-конструктор", "клиент собирает флаг сам и видит итог"),
        ("Микроразметка товара", "цена попадает прямо в сниппет Яндекса"),
        ("Свежие статьи и сезонные страницы", "обновляются, а не «умирают» после праздника"),
        ("Лёгкие и быстрые страницы", "72 КБ и ~0,8 с против ваших 358 КБ и ~3 с"),
    ]:
        s.circle(rx + 58, yy + 14, 7, fill=BLUE)
        s.text(rx + 84, yy, h_, 26, "700", INK)
        s.text(rx + 84, yy + 36, b_, 22, "500", BODY)
        yy += 92

    yb = 1052
    s.rrect((M, yb, W - M, yb + 152), r=20, fill=(236, 242, 250), outline=(206, 222, 240), width=2)
    s.text(M + 48, yb + 30, "ВАШ КОЗЫРЬ, КОТОРОГО НЕТ НИ У КОГО В ТОПЕ", 20, "800", BLUE, ls=2.4)
    s.para(M + 48, yb + 70,
           "Образец за 1 час, тираж от 5 часов, полный цикл (печать + пошив + вышивка) и кейсы федерального уровня. "
           "На сайте об этом не написано ни в одном заголовке.",
           28, "700", INK, maxw=CW - 110, lh=1.4)


def s09(s, page, total):
    s.chrome(page, total)
    s.head("Где лежат деньги: 10 кластеров спроса",
           "Под сайт собрано семантическое ядро — 560+ запросов по Москве и области. "
           "Здесь укрупнённая карта спроса: где вы теряете клиентов и где ниша свободна.")

    c1, c2, c3 = 700, 260, 360
    x1, x2, x3 = M + c1, M + c1 + c2, M + c1 + c2 + c3
    y = 400
    s.rrect((M, y, W - M, y + 58), r=14, fill=PANEL2)
    for x, t in ((M + 34, "КЛАСТЕР СПРОСА"), (x1 + 24, "СПРОС"), (x2 + 24, "КОНКУРЕНЦИЯ"),
                 (x3 + 24, "ГДЕ ВЫ СЕЙЧАС")):
        s.text(x, y + 17, t, 20, "800", MUTED, ls=2.4)

    rows = [
        ("Готовые флаги — розница", 4, "средняя", "Нет товара с ценой — нет и позиции", RED),
        ("Флаги на заказ с логотипом — B2B", 3, "средняя", "Топ-10…топ-30, конверсия низкая", AMBER),
        ("Корпоративный текстиль и мерч", 4, "высокая", "Категории тонкие, тексты шаблонные", RED),
        ("Печать на ткани", 2, "низкая", "Раздел ведёт на сломанный поддомен", RED),
        ("Флагштоки и конструкции", 3, "средняя", "Категории есть, спрос не забирают", AMBER),
        ("Широкоформат и оформление событий", 3, "высокая", "Есть, но без цен и сроков", AMBER),
        ("Знамёна, вымпелы, гербы", 2, "низкая-средняя", "Есть, тексты слабые", AMBER),
        ("Интерьерный текстиль", 2, "низкая", "Есть, нет перелинковки на кейсы", AMBER),
        ("Сезонные всплески: 9 Мая, выборы, Новый год", 3, "низкая", "Страницы не обновляются после события", RED),
        ("Госзаказ 44-ФЗ / 223-ФЗ", 2, "почти нулевая", "Посадочной нет — ниша свободна", GREEN),
    ]
    y += 58
    rh = 66
    for i, (name, lvl, comp, status, col) in enumerate(rows):
        yy = y + i * rh
        if i % 2 == 1:
            s.rect((M, yy, W - M, yy + rh), fill=(251, 252, 254))
        s.line((M, yy + rh), (W - M, yy + rh), (240, 243, 248), 2)
        cy = yy + rh / 2
        s.text(M + 34, cy - 14, name, 25, "600", INK)
        for k in range(4):
            s.circle(x1 + 32 + k * 26, cy, 8, fill=BLUE if k < lvl else (223, 229, 238))
        s.text(x2 + 24, cy - 13, comp, 24, "600", BODY)
        s.circle(x3 + 30, cy, 6, fill=col)
        s.text(x3 + 52, cy - 13, status, 24, "600", col)

    s.para(M, y + len(rows) * rh + 28,
           "Точные частоты запросов, посадочные страницы и приоритеты кластеров — рабочий материал проекта: "
           "он остаётся в контуре работ и используется нами для вывода сайта в топ.",
           24, "600", BODY, maxw=CW, lh=1.42)


def s10(s, page, total):
    s.chrome(page, total)
    s.head("Как мы это чиним: 4 этапа за 90 дней",
           "Ниже — что делаем на каждом этапе и каким результатом работ его закрываем.")

    phases = [
        ("ДНИ 1–14", "Быстрые победы", BLUE, BLUE_SOFT, [
            "Убираем технические потери и точки слива заявок",
            "Возвращаем доверие: реквизиты, разметка, рабочие ссылки",
            "Делаем заявку удобной: мессенджеры, единый номер",
        ], "Технические потери закрыты, заявки не теряются"),
        ("ДНИ 15–30", "Коммерческая упаковка", BLUE, BLUE_SOFT, [
            "Цена и наличие на экране, мгновенный расчёт стоимости",
            "Витрина готовых позиций и карточки товаров",
            "Отзывы, кейсы и страница для госзаказчиков",
        ], "Страницы отвечают на вопрос покупателя до звонка"),
        ("ДНИ 31–60", "Масштабирование", BLUE, BLUE_SOFT, [
            "Расширение семантики и посадочных страниц под спрос",
            "Сезонные окна и платный трафик на горячие запросы",
            "Маркетплейсы и публикации кейсов в медиа",
        ], "Спрос и сезонные окна закрыты страницами"),
        ("ДНИ 61–90", "Системность", BLUE, BLUE_SOFT, [
            "Конверсия: формы, квизы, A/B-тесты",
            "Скорость и мобильность до «зелёных» метрик",
            "Реактивация базы клиентов и отчётность каждый месяц",
        ], "Работы идут по метрикам, результатом управляем"),
    ]
    y0, hh = 392, 740
    cw = (CW - 3 * 36) / 4
    for i, (days, ttl, col, soft, items, result) in enumerate(phases):
        x0 = M + i * (cw + 36)
        s.rrect((x0, y0, x0 + cw, y0 + hh), r=22, fill=WHITE, outline=LINE, width=2)
        s.rrect((x0, y0, x0 + cw, y0 + 14), r=7, fill=BLUE if i < 3 else INK)
        s.text(x0 + 36, y0 + 48, str(i + 1).zfill(2), 62, "900", (214, 224, 238))
        s.pill(x0 + 36, y0 + 132, days, col, soft, 20, "800")
        s.para(x0 + 36, y0 + 200, ttl, 32, "800", INK, maxw=cw - 72, lh=1.22)
        yy = y0 + 286
        for it in items:
            s.circle(x0 + 44, yy + 12, 6, fill=BLUE)
            yy = s.para(x0 + 66, yy, it, 23, "500", BODY, maxw=cw - 102, lh=1.4) + 22
        ry = y0 + hh - 150
        s.rrect((x0 + 36, ry, x0 + cw - 36, ry + 112), r=16, fill=(244, 248, 253))
        s.text(x0 + 60, ry + 22, "ИТОГ ЭТАПА", 17, "800", MUTED, ls=2.0)
        s.para(x0 + 60, ry + 54, result, 24, "700", INK, maxw=cw - 120, lh=1.3)

    s.para(M, 1158,
           "Состав работ, ТЗ разработчику, тексты и семантика ведутся нами в рабочем контуре проекта. "
           "Каждый этап закрывается отчётом: позиции, трафик, заявки по каналам, ИКС, индексация.",
           24, "600", BODY, maxw=CW, lh=1.42)


def s11(s, page, total):
    s.chrome(page, total)
    s.head("Как мы будем измерять результат",
           "В предложении нет цифр-обещаний: фиксируем базу и одни и те же точки контроля, "
           "измеряем ежемесячно и корректируем работы по факту.")

    y0, hh = 392, 608
    lw = 1180

    # --- точка отсчёта: факты аудита
    s.rrect((M, y0, M + lw, y0 + hh), r=22, fill=WHITE, outline=LINE, width=2)
    s.text(M + 48, y0 + 40, "Точка отсчёта — факты аудита на 22.09.2026", 28, "800", INK)
    facts = [
        ("Страниц в индексе Яндекса", "290, минус 64 за месяц", RED),
        ("ИКС домена", "270 против 360 у лидера", INK),
        ("Вес главной страницы", "358 КБ против 72 КБ", INK),
        ("Время отклика", "~3 с против ~0,8 с", INK),
        ("Факторы коммерческой выдачи", "8 из 8 — хуже лидера", RED),
    ]
    ry = y0 + 104
    for name, val, col in facts:
        s.rrect((M + 48, ry, M + lw - 48, ry + 76), r=16, fill=PANEL)
        s.text(M + 76, ry + 25, name, 24, "600", INK)
        s.text(M + lw - 76, ry + 25, val, 24, "800", col, anchor="ra")
        ry += 86
    s.para(M + 48, ry + 6,
           "База зафиксирована — динамику считаем от неё, а не «на глаз».",
           22, "600", MUTED, maxw=lw - 96, lh=1.36)

    # --- что измеряем каждый месяц
    rx = M + lw + 60
    rw = W - M - rx
    s.rrect((rx, y0, W - M, y0 + hh), r=22, fill=PANEL, outline=LINE, width=2)
    s.text(rx + 44, y0 + 40, "Что измеряем каждый месяц", 28, "800", INK)
    metrics = [
        ("Индексация", "сколько страниц в поиске"),
        ("Позиции по кластерам", "топ-10, Москва и область"),
        ("Коммерческие страницы", "доля страниц с ценой и наличием"),
        ("Скорость и мобильность", "ключевые метрики страниц"),
        ("Органический трафик", "переходы и запросы из поиска"),
        ("Обращения", "звонки, формы и чаты"),
    ]
    my = y0 + 104
    for t_, sub in metrics:
        s.rrect((rx + 44, my, W - M - 44, my + 72), r=16, fill=WHITE, outline=LINE, width=2)
        s.circle(rx + 76, my + 24, 6, fill=BLUE)
        s.text(rx + 96, my + 13, t_, 24, "700", INK)
        s.text(rx + 96, my + 43, sub, 20, "500", MUTED)
        my += 82

    # --- нижняя полоса: формат контроля и где появляются целевые значения
    ty = 1032
    s.rrect((M, ty, W - M, ty + 178), r=20, fill=(244, 248, 253), outline=(214, 226, 242), width=2)
    w1 = (CW - 96 - 80) / 2
    for i, (lbl, body) in enumerate([
        ("ФОРМАТ КОНТРОЛЯ",
         "Отчёт каждый месяц: индексация, позиции по приоритетным кластерам, трафик, "
         "заявки по каналам, ИКС — плюс созвон по ходу работ."),
        ("ЦЕЛЕВЫЕ ЗНАЧЕНИЯ",
         "Согласуем отдельным приложением после этапа 1 — когда фундамент закрыт и база "
         "уточнена. В предложении цифры не фиксируются."),
    ]):
        x0 = M + 48 + i * (w1 + 80)
        s.text(x0, ty + 30, lbl, 18, "800", BLUE, ls=2.2)
        s.para(x0, ty + 68, body, 23, "600", BODY, maxw=w1, lh=1.4)


def s12(s, page, total):
    s.chrome(page, total)
    s.head("Цена промедления — сезонные окна",
           "Спрос в нише резко пиковый: кто не готов к сезону, тот его просто не получает.")

    y0, hh = 392, 348
    s.rrect((M, y0, W - M, y0 + hh), r=22, fill=WHITE, outline=LINE, width=2)
    s.text(M + 48, y0 + 40, "Календарь спроса на 12 месяцев", 28, "800", INK)
    s.text(W - M - 48, y0 + 46, "пики отмечены красным", 21, "600", MUTED, anchor="ra")

    line_y = y0 + 196
    x_start, x_end = M + 48 + 108, W - M - 48 - 108
    s.line((x_start, line_y), (x_end, line_y), (220, 228, 238), 3)
    seasons = [
        ("23 ФЕВ", "корпоративные подарки", False),
        ("8 МАРТА", "платки, вымпелы", False),
        ("ВЫПУСКНЫЕ", "июнь, школы и вузы", False),
        ("9 МАЯ", "знамёна, ленты — пик года", True),
        ("12 ИЮНЯ", "День России", True),
        ("22 АВГ", "День флага", False),
        ("1 СЕН", "флаги для школ", False),
        ("ВЫБОРЫ", "штабы и партии", True),
        ("НОВЫЙ ГОД", "мерч и декор", False),
    ]
    n = len(seasons)
    for i, (d, sub, peak) in enumerate(seasons):
        cx = x_start + (x_end - x_start) * i / (n - 1)
        if peak:
            s.circle(cx, line_y, 20, fill=RED_SOFT)
            s.circle(cx, line_y, 11, fill=RED)
        else:
            s.circle(cx, line_y, 14, fill=WHITE, outline=(176, 190, 210), width=4)
            s.circle(cx, line_y, 6, fill=(176, 190, 210))
        s.text(cx, line_y - 78, d, 24, "800", RED if peak else INK, anchor="ma")
        s.para(cx - 104, line_y + 34, sub, 20, "500", MUTED, maxw=208, lh=1.28, align="c")

    cards = [
        ("−64 страницы", "за последний месяц", "Индекс Яндекса уже сократился: если динамика сохранится, к сезону точек входа в выдаче станет меньше.", RED, RED_SOFT),
        ("Ежедневные клики", "уходят в ошибку", "Сломанный раздел меню и закрытые от поиска фотографии работают против вас каждый день.", AMBER, AMBER_SOFT),
        ("Выдача закрепляется", "за конкурентами", "Отзывы, наличие и цены соперников накапливаются: с каждым месяцем догнать их дороже.", BLUE, BLUE_SOFT),
    ]
    cw = (CW - 2 * 44) / 3
    yb = 772
    for i, (t1, t2, body, col, soft) in enumerate(cards):
        x0 = M + i * (cw + 44)
        s.rrect((x0, yb, x0 + cw, yb + 300), r=22, fill=WHITE, outline=LINE, width=2)
        s.rrect((x0 + 44, yb + 44, x0 + 44 + 84, yb + 44 + 8), r=4, fill=col)
        s.text(x0 + 44, yb + 78, t1, 44, "900", col)
        s.text(x0 + 44, yb + 136, t2, 26, "600", MUTED)
        s.para(x0 + 44, yb + 196, body, 24, "500", BODY, maxw=cw - 88, lh=1.44)

    s.para(M, 1112,
           "Работы в поиске не дают мгновенного эффекта: страницам нужно время на переиндексацию "
           "и набор позиций. Чтобы успеть к пику спроса 9 Мая, стартовать нужно в январе–феврале; "
           "к выборным кампаниям — ещё раньше.",
           26, "700", INK, maxw=CW, lh=1.42)


def s13(s, page, total):
    s.chrome(page, total)
    s.head("Следующие шаги",
           "Четыре простых действия, чтобы этап 1 начался на этой неделе.")

    y0, hh = 392, 668
    lw = 1180
    s.rrect((M, y0, M + lw, y0 + hh), r=22, fill=WHITE, outline=LINE, width=2)
    s.text(M + 48, y0 + 44, "Что нужно для старта", 32, "800", INK)
    steps = [
        ("Согласовать этап 1", "Договор и счёт. Старт работ в течение трёх рабочих дней после подписания."),
        ("Дать доступы", "Хостинг, CMS, Яндекс.Вебмастер и Метрика. Либо добавим вашего специалиста — как удобнее."),
        ("Передать материалы", "Реквизиты ООО, прайс по ходовым позициям, свежие фото производства, благодарности и сертификаты."),
        ("Договориться об отчётности", "Ежемесячный отчёт по позициям, трафику и заявкам плюс созвон по ходу работ."),
    ]
    yy = y0 + 132
    for i, (h_, b_) in enumerate(steps, start=1):
        s.mark_num(M + 78, yy + 22, i, r=27, color=BLUE, bg=BLUE_SOFT, size=26)
        s.text(M + 130, yy, h_, 29, "800", INK)
        s.para(M + 130, yy + 44, b_, 24, "500", BODY, maxw=lw - 210, lh=1.42)
        yy += 132

    rx = M + lw + 60
    rw = W - M - rx
    s.rrect((rx, y0, W - M, y0 + 330), r=22, fill=PANEL, outline=LINE, width=2)
    s.text(rx + 44, y0 + 44, "Остаётся в рабочем контуре проекта", 27, "800", INK)
    chips = [
        "Аудит — 12 разделов",
        "План — 30 задач",
        "ТЗ разработчику",
        "Ядро — 560+ запросов",
        "Контент-план — 12 статей",
        "Шаблоны разметки и скорости",
    ]
    cxp, cyp = rx + 44, y0 + 108
    for i, c_ in enumerate(chips):
        col_i, row_i = i % 2, i // 2
        wch = (rw - 88 - 20) / 2
        bx = cxp + col_i * (wch + 20)
        by = cyp + row_i * 62
        s.rrect((bx, by, bx + wch, by + 52), r=14, fill=WHITE, outline=LINE, width=2)
        s.circle(bx + 24, by + 26, 6, fill=BLUE)
        s.text(bx + 42, by + 14, c_, 21, "600", BODY)
    s.para(rx + 44, y0 + 296, "Эти материалы ведём мы — в PDF они намеренно не раскрываются.",
           20, "600", MUTED, maxw=rw - 88, lh=1.3)

    cy = y0 + 362
    s.rrect((rx, cy, W - M, cy + 306), r=22, fill=(17, 42, 79))
    s.rect((rx + 44, cy + 44, rx + 44 + 60, cy + 44 + 8), fill=(126, 170, 230))
    s.text(rx + 44, cy + 72, "Этап 1 можно начать на этой неделе", 28, "800", WHITE)
    s.text(rx + 44, cy + 128, "+7 925 090-95-00", 52, "900", WHITE)
    s.text(rx + 44, cy + 202, "звонок · WhatsApp · Telegram", 24, "600", (168, 194, 228))
    s.text(rx + 44, cy + 244, "smartsolutions.today", 26, "800", (126, 170, 230))

    s.para(M, 1092,
           "Полный комплект рабочих материалов — аудит, план работ, ТЗ разработчику, семантическое ядро "
           "и контент-план — передаётся в проект после старта и остаётся в контуре работ.",
           24, "600", BODY, maxw=CW, lh=1.42)
    s.para(M, 1168,
           "Ориентиры по трафику и заявкам в предложении не фиксируются: потенциал считаем отдельным "
           "приложением после этапа 1, от уточнённой базы.",
           21, "500", MUTED, maxw=CW, lh=1.36)


SLIDES = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12, s13]


def build_pdf(paths):
    doc = pymupdf.open()
    doc.set_metadata({
        "title": "proflag.ru — аудит сайта: диагностика и план роста на 90 дней",
        "author": "Smart Solutions · smartsolutions.today",
        "subject": "Конфиденциально. Подготовлено для ООО «Профлаг». Аудит от 22.09.2026",
        "keywords": "аудит сайта, SEO, proflag.ru, конфиденциально",
        "creator": "Smart Solutions",
        "producer": "Smart Solutions",
    })
    for p in paths:
        page = doc.new_page(width=PAGE_W_PT, height=PAGE_H_PT)
        page.insert_image(pymupdf.Rect(0, 0, PAGE_W_PT, PAGE_H_PT), filename=p)
    # Страницы — растр без текстового слоя; дополнительно запрещаем копирование и правки.
    perms = pymupdf.PDF_PERM_PRINT | pymupdf.PDF_PERM_PRINT_HQ | pymupdf.PDF_PERM_ACCESSIBILITY
    doc.save(PDF_OUT, garbage=4, deflate=True,
             encryption=pymupdf.PDF_ENCRYPT_AES_256,
             owner_pw=OWNER_PW, user_pw="", permissions=perms)
    doc.close()
    print("PDF: %s (%.2f МБ)" % (PDF_OUT, os.path.getsize(PDF_OUT) / 1048576))


def main():
    os.makedirs(PNG_DIR, exist_ok=True)
    total = len(SLIDES)
    paths = []
    for i, fn in enumerate(SLIDES, start=1):
        s = Slide()
        fn(s, i, total)
        p = os.path.join(PNG_DIR, "slide-%02d.png" % i)
        s.save(p)
        paths.append(p)
        print("слайд %02d → %s" % (i, os.path.basename(p)))
    build_pdf(paths)


if __name__ == "__main__":
    main()
