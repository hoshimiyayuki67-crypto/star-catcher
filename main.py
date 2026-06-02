from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty
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

Window.size = (360, 640)

# ===== 星星类型配置 =====
STAR_TYPES = {
    'gold':  {'color': (1, 0.84, 0, 1),   'points': 1, 'size': 28, 'label': '⭐', 'speed_range': (3, 6)},
    'silver':{'color': (0.75, 0.75, 1, 1), 'points': 2, 'size': 22, 'label': '✨', 'speed_range': (4, 7)},
    'red':   {'color': (1, 0.3, 0.3, 1),   'points': 3, 'size': 32, 'label': '🔥', 'speed_range': (5, 8)},
}

# ===== 粒子类 =====
class Particle(Widget):
    def __init__(self, x, y, color, **kwargs):
        super().__init__(**kwargs)
        self.pos = (x, y)
        self.size = (6, 6)
        self.color = color
        self.life = 1.0
        self.vx = uniform(-3, 3)
        self.vy = uniform(2, 6)
        with self.canvas:
            Color(*color)
            self.rect = Ellipse(pos=self.pos, size=self.size)

    def update(self):
        self.life -= 0.03
        self.x += self.vx
        self.y += self.vy
        self.vy -= 0.2  # 重力
        s = max(2, self.size[0] * self.life)
        self.size = (s, s)
        self.canvas.clear()
        with self.canvas:
            Color(*self.color, self.life)
            Ellipse(pos=self.pos, size=self.size)
        return self.life > 0

# ===== 星星类 =====
class Star(Widget):
    def __init__(self, star_type='gold', **kwargs):
        super().__init__(**kwargs)
        cfg = STAR_TYPES[star_type]
        self.star_type = star_type
        self.points = cfg['points']
        s = cfg['size']
        self.size = (s, s)
        self.color = cfg['color']
        speed = randint(*cfg['speed_range'])
        self.velocity = (0, -speed)
        self.angle = 0
        self.label = cfg['label']
        self.drawn = False

    def move(self):
        self.pos = Vector(*self.velocity) + self.pos
        self.angle += 5  # 旋转效果

    def draw(self):
        self.canvas.clear()
        with self.canvas:
            Color(*self.color)
            cx, cy = self.center_x - self.x, self.center_y - self.y
            r = self.width / 2
            # 画星星（五角星）
            points = []
            for i in range(10):
                angle = radians(self.angle + i * 36)
                radius = r if i % 2 == 0 else r * 0.4
                px = self.center_x + cos(angle) * radius
                py = self.center_y + sin(angle) * radius
                points.extend([px, py])
            Line(points=points, close=True, width=1.5)
            # 发光效果（内圆）
            Color(*self.color, 0.3)
            Ellipse(pos=(self.x - 2, self.y - 2), size=(self.width + 4, self.height + 4))

# ===== 船类 =====
class Boat(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (90, 40)
        self.bob_offset = 0
        self.draw_boat()

    def draw_boat(self):
        self.canvas.clear()
        with self.canvas:
            # 船身（深蓝色）
            Color(0.15, 0.4, 0.8, 1)
            Rectangle(pos=(self.x, self.y + 5), size=(self.width, 15))
            # 船头
            Color(0.2, 0.5, 0.9, 1)
            Triangle(points=[
                self.x + self.width, self.y + 5,
                self.x + self.width, self.y + 20,
                self.x + self.width + 15, self.y + 12
            ])
            # 船帆（白色三角形）
            Color(0.95, 0.95, 1, 1)
            Triangle(points=[
                self.x + 25, self.y + 20,
                self.x + 25, self.y + 45,
                self.x + 55, self.y + 28
            ])
            # 桅杆
            Color(0.6, 0.4, 0.2, 1)
            Rectangle(pos=(self.x + 23, self.y + 15), size=(4, 35))
            # 船底
            Color(0.1, 0.3, 0.6, 1)
            Rectangle(pos=(self.x, self.y), size=(self.width - 5, 7))

    def update_pos(self):
        self.draw_boat()

# ===== 游戏主界面 =====
class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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

        # 背景
        with self.canvas:
            # 天空渐变
            Color(0.05, 0.05, 0.2, 1)
            Rectangle(pos=(0, self.height * 0.4), size=(self.width, self.height * 0.6))
            Color(0.1, 0.1, 0.3, 1)
            Rectangle(pos=(0, self.height * 0.2), size=(self.width, self.height * 0.2))
            # 海面
            Color(0.05, 0.15, 0.4, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height * 0.2))

        # UI
        self.score_label = Label(text="⭐ 0", pos=(10, self.height - 50), size_hint=(None, None),
                                 font_size=22, color=(1, 1, 1, 1), bold=True)
        self.add_widget(self.score_label)

        self.combo_label = Label(text="", pos=(self.width/2, self.height - 50), size_hint=(None, None),
                                 font_size=18, color=(1, 0.84, 0, 1), halign='center')
        self.add_widget(self.combo_label)

        self.life_label = Label(text="❤️❤️❤️❤️❤️", pos=(self.width - 150, self.height - 50), size_hint=(None, None),
                                font_size=16, color=(1, 0.3, 0.3, 1))
        self.add_widget(self.life_label)

        self.level_label = Label(text="Lv.1", pos=(self.width/2, 5), size_hint=(None, None),
                                 font_size=14, color=(0.6, 0.8, 1, 1), halign='center')
        self.add_widget(self.level_label)

        Clock.schedule_interval(self.update, 1.0 / 60.0)
        Clock.schedule_interval(self.spawn_star, self.spawn_rate)

    def load_high_score(self):
        try:
            if os.path.exists('star_catcher_score.json'):
                with open('star_catcher_score.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('high_score', 0)
        except:
            pass

    def save_high_score(self):
        try:
            with open('star_catcher_score.json', 'w') as f:
                json.dump({'high_score': self.high_score}, f)
        except:
            pass

    def spawn_star(self, dt):
        if self.game_over:
            return
        # 随机选择星星类型
        r = randint(1, 100)
        if r <= 70:
            st = 'gold'
        elif r <= 92:
            st = 'silver'
        else:
            st = 'red'

        star = Star(st)
        star.x = randint(20, self.width - star.width - 20)
        star.top = 0
        star.draw()
        self.add_widget(star)
        self.stars.append(star)

    def spawn_particles(self, x, y, color, count=8):
        for _ in range(count):
            p = Particle(x, y, color)
            self.add_widget(p)
            self.particles.append(p)

    def update(self, dt):
        if self.game_over:
            # 更新粒子
            self.particles = [p for p in self.particles if p.update()]
            return

        # 移动船
        speed = 6
        if 'left' in self.pressed_keys and self.boat.x > 0:
            self.boat.x -= speed
        if 'right' in self.pressed_keys and self.boat.x < self.width - self.boat.width:
            self.boat.x += speed
        self.boat.update_pos()

        # 更新星星
        stars_to_remove = []
        for star in self.stars[:]:
            star.move()
            star.draw()

            if star.collide_widget(self.boat):
                self.score += star.points
                self.total_caught += 1
                self.combo += 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                # 连击加分
                bonus = min(self.combo // 3, 5)
                total_pts = star.points + bonus
                self.score += bonus

                self.spawn_particles(star.center_x, star.center_y, star.color)
                stars_to_remove.append(star)

                self.score_label.text = f"⭐ {self.score}"
                if self.combo >= 3:
                    self.combo_label.text = f"🔥 {self.combo}连击!"
                else:
                    self.combo_label.text = ""

                # 增加难度
                self.difficulty_timer += 1
                if self.difficulty_timer % 8 == 0 and self.spawn_rate > 0.2:
                    self.spawn_rate = max(0.2, self.spawn_rate - 0.04)
                    Clock.unschedule(self.spawn_star)
                    Clock.schedule_interval(self.spawn_star, self.spawn_rate)
                    self.level += 1
                    self.level_label.text = f"Lv.{self.level}"

            elif star.y < -50:
                stars_to_remove.append(star)
                self.missed += 1
                self.combo = 0
                self.combo_label.text = ""
                self.update_life_display()
                if self.missed >= self.max_miss:
                    self.game_over_func()
                    return

        for star in stars_to_remove:
            if star in self.stars:
                self.stars.remove(star)
                self.remove_widget(star)

        # 更新粒子
        self.particles = [p for p in self.particles if p.update()]

        # UI位置
        self.score_label.pos = (10, self.height - 50)
        self.combo_label.pos = (self.width/2 - 50, self.height - 50)
        self.life_label.pos = (self.width - 150, self.height - 50)
        self.level_label.pos = (self.width/2 - 20, 5)

    def update_life_display(self):
        lives = self.max_miss - self.missed
        self.life_label.text = "❤️" * max(0, lives) + "🖤" * max(0, self.missed)

    def on_touch_move(self, touch):
        if not self.game_over:
            self.boat.center_x = touch.x

    def on_touch_down(self, touch):
        if self.game_over:
            self.restart_game()
        elif not self.game_over:
            self.boat.center_x = touch.x

    def _on_keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard = None

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'left':
            self.pressed_keys.add('left')
        elif keycode[1] == 'right':
            self.pressed_keys.add('right')
        return True

    def _on_key_up(self, keyboard, keycode):
        if keycode[1] == 'left':
            self.pressed_keys.discard('left')
        elif keycode[1] == 'right':
            self.pressed_keys.discard('right')
        return True

    def game_over_func(self):
        self.game_over = True
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

        self.clear_widgets()

        # 游戏结束背景
        with self.canvas:
            Color(0, 0, 0, 0.8)
            Rectangle(pos=(0, 0), size=(self.width, self.height))

        layout = BoxLayout(orientation='vertical', spacing=12, padding=40)
        layout.size_hint = (0.8, 0.7)
        layout.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        title = Label(text="🎮 游戏结束", font_size=38, color=(1, 0.3, 0.3, 1),
                      size_hint=(1, 0.2), bold=True)
        score_text = (f"⭐ 得分: {self.score}\n"
                      f"🏆 最高分: {self.high_score}\n"
                      f"📊 接住: {self.total_caught} 颗\n"
                      f"🔥 最高连击: {self.max_combo}\n"
                      f"📈 达到等级: Lv.{self.level}")
        score_lbl = Label(text=score_text, font_size=18, color=(1, 1, 1, 1),
                          size_hint=(1, 0.5), halign='center')
        score_lbl.bind(size=lambda s, w: setattr(s, 'text_size', (s.width, None)))

        restart_btn = Button(text="🔄 再来一局", font_size=22,
                             size_hint=(0.7, 0.15),
                             pos_hint={'center_x': 0.5},
                             background_color=(0.2, 0.6, 1, 1),
                             background_normal='')
        restart_btn.bind(on_press=lambda x: self.restart_game())

        layout.add_widget(title)
        layout.add_widget(score_lbl)
        layout.add_widget(restart_btn)
        self.add_widget(layout)

    def restart_game(self):
        for star in self.stars[:]:
            self.remove_widget(star)
        self.stars.clear()
        for p in self.particles[:]:
            self.remove_widget(p)
        self.particles.clear()

        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.missed = 0
        self.total_caught = 0
        self.level = 1
        self.spawn_rate = 0.9
        self.difficulty_timer = 0
        self.game_over = False

        self.clear_widgets()

        with self.canvas:
            Color(0.05, 0.05, 0.2, 1)
            Rectangle(pos=(0, self.height * 0.4), size=(self.width, self.height * 0.6))
            Color(0.1, 0.1, 0.3, 1)
            Rectangle(pos=(0, self.height * 0.2), size=(self.width, self.height * 0.2))
            Color(0.05, 0.15, 0.4, 1)
            Rectangle(pos=(0, 0), size=(self.width, self.height * 0.2))

        self.boat = Boat()
        self.boat.center_x = self.width / 2
        self.boat.y = 50
        self.add_widget(self.boat)

        self.score_label = Label(text="⭐ 0", pos=(10, self.height - 50), size_hint=(None, None),
                                 font_size=22, color=(1, 1, 1, 1), bold=True)
        self.add_widget(self.score_label)
        self.combo_label = Label(text="", pos=(self.width/2, self.height - 50), size_hint=(None, None),
                                 font_size=18, color=(1, 0.84, 0, 1), halign='center')
        self.add_widget(self.combo_label)
        self.life_label = Label(text="❤️❤️❤️❤️❤️", pos=(self.width - 150, self.height - 50), size_hint=(None, None),
                                font_size=16, color=(1, 0.3, 0.3, 1))
        self.add_widget(self.life_label)
        self.level_label = Label(text="Lv.1", pos=(self.width/2, 5), size_hint=(None, None),
                                 font_size=14, color=(0.6, 0.8, 1, 1), halign='center')
        self.add_widget(self.level_label)

        Clock.schedule_interval(self.spawn_star, self.spawn_rate)


class StarCatcherApp(App):
    def build(self):
        self.title = "接星星 ⭐"
        game = GameWidget()
        game.boat = Boat()
        game.boat.center_x = game.width / 2
        game.boat.y = 50
        game.add_widget(game.boat)

        help_label = Label(text="👆 触摸移动 | ← → 方向键",
                           pos=(0, 30), size_hint=(None, None),
                           font_size=14, color=(0.8, 0.8, 0.8, 1))
        game.add_widget(help_label)

        return game


if __name__ == '__main__':
    StarCatcherApp().run()
