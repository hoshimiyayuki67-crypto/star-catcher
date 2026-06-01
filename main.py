from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle, Ellipse, Triangle
from random import randint
import json
import os

# 设置窗口大小
Window.size = (360, 640)

class Star(Widget):
    """天上掉下来的星星"""
    vel_x = NumericProperty(0)
    vel_y = NumericProperty(0)
    velocity = ReferenceListProperty(vel_x, vel_y)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (30, 30)
        with self.canvas:
            Color(1, 0.84, 0, 1)  # 金色
            Ellipse(pos=self.pos, size=self.size)
    
    def move(self):
        self.pos = Vector(*self.velocity) + self.pos

class Boat(Widget):
    """玩家控制的小船"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (80, 30)
        with self.canvas:
            # 船身
            Color(0.2, 0.6, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            # 船帆
            Color(1, 1, 1, 1)
            Triangle(
                points=[
                    self.x + 20, self.y + 30,
                    self.x + 20, self.y + 5,
                    self.x + 50, self.y + 17
                ]
            )

class GameWidget(Widget):
    """游戏主界面"""
    star = ObjectProperty(None)
    boat = ObjectProperty(None)
    score = NumericProperty(0)
    high_score = NumericProperty(0)
    game_over = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        self._keyboard.bind(on_key_up=self._on_key_up)
        self.pressed_keys = set()
        self.stars = []
        self.spawn_rate = 0.8
        self.difficulty_timer = 0
        
        # 加载最高分
        self.load_high_score()
        
        # 显示分数
        self.score_label = Label(
            text=f"⭐ 得分: 0",
            pos=(10, self.height - 40),
            size_hint=(None, None),
            font_size=20,
            color=(1, 1, 1, 1)
        )
        self.add_widget(self.score_label)
        
        # 开始游戏
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
        if not self.game_over:
            star = Star()
            star.x = randint(0, self.width - star.width)
            star.top = 0
            speed = randint(3, 7)
            star.velocity = (0, -speed)
            self.add_widget(star)
            self.stars.append(star)
    
    def update(self, dt):
        if self.game_over:
            return
        
        # 移动小船
        if 'left' in self.pressed_keys and self.boat.x > 0:
            self.boat.x -= 5
        if 'right' in self.pressed_keys and self.boat.x < self.width - self.boat.width:
            self.boat.x += 5
        
        # 更新小船图形位置
        self.boat.canvas.clear()
        with self.boat.canvas:
            Color(0.2, 0.6, 1, 1)
            Rectangle(pos=self.boat.pos, size=self.boat.size)
            Color(1, 1, 1, 1)
            Triangle(
                points=[
                    self.boat.x + 20, self.boat.y + 30,
                    self.boat.x + 20, self.boat.y + 5,
                    self.boat.x + 50, self.boat.y + 17
                ]
            )
        
        # 移动星星
        stars_to_remove = []
        for star in self.stars[:]:
            star.move()
            star.canvas.clear()
            with star.canvas:
                Color(1, 0.84, 0, 1)
                Ellipse(pos=star.pos, size=star.size)
            
            # 检测碰撞
            if star.collide_widget(self.boat):
                self.score += 1
                self.score_label.text = f"⭐ 得分: {self.score}"
                stars_to_remove.append(star)
                # 增加难度
                self.difficulty_timer += 1
                if self.difficulty_timer % 5 == 0 and self.spawn_rate > 0.2:
                    self.spawn_rate -= 0.05
                    Clock.unschedule(self.spawn_star)
                    Clock.schedule_interval(self.spawn_star, self.spawn_rate)
            
            # 星星掉到底部
            elif star.y < -50:
                stars_to_remove.append(star)
        
        for star in stars_to_remove:
            if star in self.stars:
                self.stars.remove(star)
                self.remove_widget(star)
        
        # 更新分数标签位置
        self.score_label.pos = (10, self.height - 40)
    
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
        
        # 显示游戏结束界面
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', spacing=20, padding=50)
        
        title = Label(
            text=f"游戏结束！",
            font_size=40,
            color=(1, 0.3, 0.3, 1),
            size_hint=(1, 0.3)
        )
        score_label = Label(
            text=f"得分: {self.score}\n最高分: {self.high_score}",
            font_size=24,
            color=(1, 1, 1, 1),
            size_hint=(1, 0.3)
        )
        restart_btn = Button(
            text="重新开始",
            font_size=24,
            size_hint=(0.6, 0.15),
            pos_hint={'center_x': 0.5},
            background_color=(0.2, 0.6, 1, 1)
        )
        restart_btn.bind(on_press=lambda x: self.restart_game())
        
        layout.add_widget(title)
        layout.add_widget(score_label)
        layout.add_widget(restart_btn)
        self.add_widget(layout)
    
    def restart_game(self):
        # 重置游戏
        for star in self.stars[:]:
            self.remove_widget(star)
        self.stars.clear()
        self.score = 0
        self.game_over = False
        self.spawn_rate = 0.8
        self.difficulty_timer = 0
        
        self.clear_widgets()
        
        # 重新创建小船
        self.boat = Boat()
        self.boat.center_x = self.width / 2
        self.boat.y = 50
        self.add_widget(self.boat)
        
        # 分数标签
        self.score_label = Label(
            text=f"⭐ 得分: 0",
            pos=(10, self.height - 40),
            size_hint=(None, None),
            font_size=20,
            color=(1, 1, 1, 1)
        )
        self.add_widget(self.score_label)
        
        Clock.schedule_interval(self.spawn_star, self.spawn_rate)

class StarCatcherApp(App):
    def build(self):
        self.title = "接星星 ⭐"
        game = GameWidget()
        game.boat = Boat()
        game.boat.center_x = game.width / 2
        game.boat.y = 50
        game.add_widget(game.boat)
        
        # 初始提示
        help_label = Label(
            text="← → 移动 | 点击屏幕移动",
            pos=(0, 30),
            size_hint=(None, None),
            font_size=14,
            color=(0.8, 0.8, 0.8, 1)
        )
        game.add_widget(help_label)
        
        return game

if __name__ == '__main__':
    StarCatcherApp().run()
