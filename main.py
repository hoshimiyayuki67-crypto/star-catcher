from kivy.app import App
from kivy.uix.widget import Widget
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle, Ellipse, Triangle, Line
from random import randint, uniform
from math import sin, cos, radians
import json
import os

# ===== 自适应分辨率 =====
# 以360x640为基准
BASE_W, BASE_H = 360, 640

def scale(val, axis='x'):
    if axis == 'x':
        return val * Window.width / BASE_W
    return val * Window.height / BASE_H

def s(val):
    """简写 - 基于窗口宽度的等比缩放"""
    return int(val * min(Window.width/BASE_W, Window.height/BASE_H))

def sx(val):
    return int(val * Window.width / BASE_W)

def sy(val):
    return int(val * Window.height / BASE_H)

# ===== 星星类型 =====
STAR_TYPES = {
    'gold':  {'color': (1, 0.84, 0, 1),   'points': 1, 'size': s(28), 'speed': (3, 6)},
    'silver':{'color': (0.75, 0.75, 1, 1), 'points': 2, 'size': s(22), 'speed': (4, 7)},
    'red':   {'color': (1, 0.3, 0.3, 1),   'points': 3, 'size': s(32), 'speed': (5, 8)},
}

# ===== 粒子 =====
class Particle(Widget):
    def __init__(self, x, y, color, **kwargs):
        super().__init__(**kwargs)
        self.pos = (x-s(3), y-s(3))
        self.size = (s(6), s(6))
        self.r, self.g, self.b, self.a = color
        self.life = 1.0
        self.vx = uniform(-s(4), s(4))
        self.vy = uniform(s(2), s(7))

    def update(self):
        self.life -= 0.04
        self.x += self.vx
        self.y += self.vy
        self.vy -= s(0.25)
        sz = max(s(2), self.width * self.life)
        self.size = (sz, sz)
        self.canvas.clear()
        with self.canvas:
            Color(self.r, self.g, self.b, max(0, self.life))
            Ellipse(pos=self.pos, size=self.size)
        return self.life > 0

# ===== 星星 =====
class Star(Widget):
    def __init__(self, star_type='gold', **kwargs):
        super().__init__(**kwargs)
        cfg = STAR_TYPES[star_type]
        self.points_val = cfg['points']
        siz = cfg['size']
        self.size = (siz, siz)
        self.r, self.g, self.b, self.a = cfg['color']
        spd = randint(*cfg['speed'])
        self.velocity = (0, -spd * Window.height / BASE_H)
        self.angle = randint(0, 360)

    def move(self):
        self.pos = Vector(*self.velocity) + self.pos
        self.angle += 8

    def redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(self.r, self.g, self.b, 0.3)
            Ellipse(pos=(self.x-s(3), self.y-s(3)), size=(self.width+s(6), self.height+s(6)))
            Color(self.r, self.g, self.b, 1)
            cx, cy = self.center_x, self.center_y
            pts = []
            for i in range(10):
                a = radians(self.angle + i * 36)
                radius = self.width/2 if i%2==0 else self.width*0.35
                pts.extend([cx + cos(a)*radius, cy + sin(a)*radius])
            Line(points=pts, close=True, width=s(2))

# ===== 小船 =====
class Boat(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (sx(90), sy(50))

    def redraw(self):
        self.canvas.clear()
        x, y, w = self.x, self.y, self.width
        with self.canvas:
            Color(0.1, 0.25, 0.55, 1)
            Rectangle(pos=(x+sx(5), y), size=(sx(75), sy(8)))
            Color(0.15, 0.4, 0.8, 1)
            Rectangle(pos=(x+sx(3), y+sy(6)), size=(sx(78), sy(14)))
            Color(0.2, 0.5, 0.9, 1)
            Triangle(points=[x+sx(80), y+sy(6), x+sx(80), y+sy(20), x+sx(92), y+sy(13)])
            Color(0.5, 0.35, 0.15, 1)
            Rectangle(pos=(x+sx(28), y+sy(8)), size=(sx(5), sy(32)))
            Color(0.95, 0.95, 1, 1)
            Triangle(points=[x+sx(30), y+sy(18), x+sx(30), y+sy(40), x+sx(58), y+sy(26)])
            Color(0.9, 0.9, 0.98, 1)
            Triangle(points=[x+sx(30), y+sy(18), x+sx(30), y+sy(40), x+sx(52), y+sy(22)])

# ===== 游戏主界面 =====
class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = Window.size
        self.w, self.h = self.size

        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        self._keyboard.bind(on_key_up=self._on_key_up)
        self.pressed_keys = set()
        self.stars = []
        self.particles = []
        self.score = 0
        self.high_score = 0
        self.combo = 0
        self.max_combo = 0
        self.missed = 0
        self.max_miss = 5
        self.spawn_rate = 0.9
        self.difficulty_timer = 0
        self.level = 1
        self.game_over = False
        self.total_caught = 0

        self.load_high_score()
        self.draw_background()

        fs = s(22)
        self.score_label = Label(text="⭐ 0",
            pos=(sx(10), self.h-sy(45)), size_hint=(None, None),
            font_size=fs, color=(1,1,1,1), bold=True)
        self.add_widget(self.score_label)

        self.combo_label = Label(text="", size_hint=(None, None),
            pos=(self.w//2 - sx(40), self.h-sy(45)),
            font_size=s(18), color=(1,0.84,0,1))
        self.add_widget(self.combo_label)

        self.life_label = Label(text="❤️❤️❤️❤️❤️",
            pos=(self.w - sx(140), self.h-sy(45)), size_hint=(None, None),
            font_size=s(16), color=(1,0.3,0.3,1))
        self.add_widget(self.life_label)

        self.level_label = Label(text="Lv.1",
            pos=(self.w//2 - sx(15), sy(5)), size_hint=(None, None),
            font_size=s(14), color=(0.6,0.8,1,1))
        self.add_widget(self.level_label)

        self.boat = Boat()
        self.boat.center_x = self.w / 2
        self.boat.y = sy(30)
        self.boat.redraw()
        self.add_widget(self.boat)

        self.help_lbl = Label(text="👆 触摸移动 | ← → 方向键",
            pos=(self.w//2 - sx(80), sy(60)), size_hint=(None, None),
            font_size=s(14), color=(0.8,0.8,0.8,1))
        self.add_widget(self.help_lbl)

        Clock.schedule_interval(self.update, 1.0/60.0)
        Clock.schedule_interval(self.spawn_star, self.spawn_rate)

    def draw_background(self):
        with self.canvas:
            Color(0.02, 0.02, 0.15, 1)
            Rectangle(pos=(0, self.h//2), size=(self.w, self.h//2))
            from random import random
            Color(1,1,1,0.3)
            for _ in range(s(20)):
                x = random() * self.w
                y = self.h//2 + random() * self.h//2
                Ellipse(pos=(x,y), size=(s(2),s(2)))
            Color(0.05, 0.08, 0.25, 1)
            Rectangle(pos=(0, self.h//4), size=(self.w, self.h//4))
            Color(0.03, 0.1, 0.35, 1)
            Rectangle(pos=(0, 0), size=(self.w, self.h//4))

    def load_high_score(self):
        try:
            if os.path.exists('star_catcher_score.json'):
                with open('star_catcher_score.json') as f:
                    self.high_score = json.load(f).get('high_score', 0)
        except: pass
    def save_high_score(self):
        try:
            with open('star_catcher_score.json', 'w') as f:
                json.dump({'high_score': self.high_score}, f)
        except: pass

    def spawn_star(self, dt):
        if self.game_over: return
        r = randint(1,100)
        st = 'gold' if r<=70 else ('silver' if r<=92 else 'red')
        star = Star(st)
        star.x = randint(s(20), self.w - star.width - s(20))
        star.top = 0
        star.redraw()
        self.add_widget(star)
        self.stars.append(star)

    def spawn_particles(self, x, y, color):
        for _ in range(s(10)):
            p = Particle(x, y, color)
            self.add_widget(p)
            self.particles.append(p)

    def update(self, dt):
        if self.game_over:
            self.particles = [p for p in self.particles if p.update()]
            return
        spd = sx(6)
        if 'left' in self.pressed_keys and self.boat.x > 0:
            self.boat.x -= spd
        if 'right' in self.pressed_keys and self.boat.x < self.w - self.boat.width:
            self.boat.x += spd
        self.boat.redraw()
        to_rm = []
        for star in self.stars[:]:
            star.move()
            star.redraw()
            if star.collide_widget(self.boat):
                self.score += star.points_val
                self.total_caught += 1
                self.combo += 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                bonus = min(self.combo // 3, 5)
                self.score += bonus
                self.spawn_particles(star.center_x, star.center_y, star.color)
                to_rm.append(star)
                self.score_label.text = f"⭐ {self.score}"
                self.combo_label.text = f"🔥 {self.combo}连!" if self.combo>=3 else ""
                self.difficulty_timer += 1
                if self.difficulty_timer % 8 == 0 and self.spawn_rate > 0.2:
                    self.spawn_rate = max(0.2, self.spawn_rate - 0.04)
                    Clock.unschedule(self.spawn_star)
                    Clock.schedule_interval(self.spawn_star, self.spawn_rate)
                    self.level += 1
                    self.level_label.text = f"Lv.{self.level}"
            elif star.y < -s(50):
                to_rm.append(star)
                self.missed += 1
                self.combo = 0
                self.combo_label.text = ""
                self.life_label.text = "❤️"*max(0,self.max_miss-self.missed) + "🖤"*self.missed
                if self.missed >= self.max_miss:
                    self.game_over_func()
                    return
        for star in to_rm:
            if star in self.stars:
                self.stars.remove(star)
                self.remove_widget(star)
        self.particles = [p for p in self.particles if p.update()]

    def on_touch_move(self, touch):
        if not self.game_over:
            self.boat.center_x = touch.x
    def on_touch_down(self, touch):
        if self.game_over:
            self.restart_game()
        elif not self.game_over:
            self.boat.center_x = touch.x
            if hasattr(self, 'help_lbl') and self.help_lbl.parent:
                self.remove_widget(self.help_lbl)
    def _on_keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_closed)
        self._keyboard = None
    def _on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'left': self.pressed_keys.add('left')
        elif keycode[1] == 'right': self.pressed_keys.add('right')
        return True
    def _on_key_up(self, keyboard, keycode):
        if keycode[1] == 'left': self.pressed_keys.discard('left')
        elif keycode[1] == 'right': self.pressed_keys.discard('right')
        return True

    def game_over_func(self):
        self.game_over = True
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
        self.clear_widgets()
        with self.canvas:
            Color(0,0,0,0.85)
            Rectangle(pos=(0,0), size=self.size)
        fs = s(18)
        layout = BoxLayout(orientation='vertical', spacing=s(10), padding=s(40))
        layout.size_hint = (0.85, 0.7)
        layout.pos_hint = {'center_x':0.5, 'center_y':0.5}
        title = Label(text="🎮 游戏结束", font_size=s(36), color=(1,0.3,0.3,1), size_hint=(1,0.2), bold=True)
        info = (f"  ⭐ 得分: {self.score}\n  🏆 最高: {self.high_score}\n"
                f"  📊 接住: {self.total_caught} 颗\n  🔥 最高连击: {self.max_combo}\n  📈 Lv.{self.level}")
        sl = Label(text=info, font_size=fs, color=(1,1,1,1), size_hint=(1,0.5), halign='center')
        sl.bind(size=lambda s,w: setattr(s,'text_size',(s.width,None)))
        btn = Button(text="🔄 再来一局", font_size=s(22), size_hint=(0.7,0.15),
                     pos_hint={'center_x':0.5}, background_color=(0.2,0.6,1,1), background_normal='')
        btn.bind(on_press=lambda x: self.restart_game())
        layout.add_widget(title); layout.add_widget(sl); layout.add_widget(btn)
        self.add_widget(layout)

    def restart_game(self):
        for s in self.stars[:]: self.remove_widget(s)
        self.stars.clear()
        for p in self.particles[:]: self.remove_widget(p)
        self.particles.clear()
        self.score=0; self.combo=0; self.max_combo=0; self.missed=0
        self.total_caught=0; self.level=1; self.spawn_rate=0.9
        self.difficulty_timer=0; self.game_over=False
        self.clear_widgets()
        self.draw_background()
        self.score_label = Label(text="⭐ 0", pos=(sx(10),self.h-sy(45)),
            size_hint=(None,None), font_size=s(22), color=(1,1,1,1), bold=True)
        self.add_widget(self.score_label)
        self.combo_label = Label(text="", pos=(self.w//2-sx(40),self.h-sy(45)),
            size_hint=(None,None), font_size=s(18), color=(1,0.84,0,1))
        self.add_widget(self.combo_label)
        self.life_label = Label(text="❤️❤️❤️❤️❤️", pos=(self.w-sx(140),self.h-sy(45)),
            size_hint=(None,None), font_size=s(16), color=(1,0.3,0.3,1))
        self.add_widget(self.life_label)
        self.level_label = Label(text="Lv.1", pos=(self.w//2-sx(15),sy(5)),
            size_hint=(None,None), font_size=s(14), color=(0.6,0.8,1,1))
        self.add_widget(self.level_label)
        self.boat = Boat()
        self.boat.center_x = self.w/2
        self.boat.y = sy(30)
        self.boat.redraw()
        self.add_widget(self.boat)
        Clock.schedule_interval(self.spawn_star, self.spawn_rate)

class StarCatcherApp(App):
    def build(self):
        self.title = "接星星 ⭐"
        return GameWidget()

if __name__ == '__main__':
    StarCatcherApp().run()
