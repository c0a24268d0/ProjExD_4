import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"  # 追加機能4: こうかとんの状態 (normal / hyper)
        self.hyper_life = 0    # 追加機能4: 無敵状態の残りフレーム数

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            # 無敵状態が終了したら元の画像に戻すため、ここでオリジナルの画像を保持
            if self.state == "normal":
                self.image = self.imgs[self.dire] 
        
        # ▼ 追加機能4：無敵状態の処理 ▼
        if self.state == "hyper":
            self.hyper_life -= 1
            # 無敵状態中は画像をラプラシアンフィルタで加工
            self.image = pg.transform.laplacian(self.imgs[self.dire]) 
            if self.hyper_life < 0:
                self.state = "normal"
                # 無敵状態終了時に画像を元に戻す
                self.image = self.imgs[self.dire] 
        # ▲ 追加機能4：無敵状態の処理 ▲

        screen.blit(self.image, self.rect)
        #  こうかとんの移動速度変更
        if key_lst[pg.K_LSHIFT] and (sum_mv[0] != 0 or sum_mv[1] != 0): #  左shiftキーが入力されているかつ、こうかとんが動いている
            move_speed = 20 #  変更後スピード
        else:
            move_speed = 10 #  変更されないときのスピード
        self.speed = move_speed


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0: float = 0): 
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        引数 angle0：ビームの回転角度（デフォルト0）
        """
        super().__init__()
        
        # ▼ 最終的な修正箇所 ▼
        # こうかとんの現在の向きから基本となる角度を計算
        # atan2(y, x)を使用し、Pygameのy軸は下方向が正なので、y成分は反転させる
        base_angle_rad = math.atan2(-bird.dire[1], bird.dire[0])
        base_angle_deg = math.degrees(base_angle_rad)
        
        # 基本角度に弾幕のオフセット角度を加算
        final_angle_deg = base_angle_deg + angle0
        
        # ビーム画像の回転
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), final_angle_deg, 1.0)
        
        # ビームの移動方向ベクトルを計算
        # ここで最終的な角度 (final_angle_deg) を使用することが重要です
        self.vx = math.cos(math.radians(final_angle_deg))
        self.vy = -math.sin(math.radians(final_angle_deg)) # PygameのY軸は下方向が正なので、sinに-を付ける
        # ▲ 最終的な修正箇所ここまで ▲
        
        self.rect = self.image.get_rect()
        # ビームの初期位置をこうかとんの進行方向の少し先に設定
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


# ▼ 追加機能6：弾幕発射のためのクラス ▼
class NeoBeam:
    """
    複数のビームを生成するクラス
    """
    def __init__(self, bird: Bird, num: int):
        """
        複数のビームを生成するための初期化
        引数1 bird：ビームを放つこうかとん
        引数2 num：生成するビームの数
        """
        self.bird = bird
        self.num = num

    def gen_beams(self) -> list[Beam]:
        """
        指定された数のビームを生成し、リストとして返す
        戻り値：生成されたBeamインスタンスのリスト
        """
        beams = []
        if self.num > 1:
            step = 100 / (self.num - 1)  # float除算に変更
        else:
            step = 0 # ビームが1つの場合はステップ不要

        for i in range(self.num):
            if self.num == 1:
                angle0 = 0
            else:
                angle0 = -50 + i * step
            beams.append(Beam(self.bird, angle0)) # Here, angle0 is passed
        return beams
# ▲ 追加機能6：弾幕発射のためのクラス ▲


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル
        #self.interval=1#お遊び

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 400
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)

class Invisible:
    def __init__(self):
        self.font=pg.font.Font(None,50)
        self.color=(255,0,0)
        self.value=0
        self.image = self.font.render(f"Invisible Time: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 400, HEIGHT-50
    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Invisible Time: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)

class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """
    def __init__(self, life: int = 400):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(255) 
        self.rect = self.image.get_rect()
        self.life = life  


    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    invisible=Invisible()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    gravitys = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    score.value=500 #デバッグ用
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            # ▼ 通常ビームの発射 ▼
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if key_lst[pg.K_LSHIFT]:
                    neo_beam = NeoBeam(bird, 5) # ビーム数5の弾幕
                    beams.add(*neo_beam.gen_beams()) # リストを展開して追加
                else:
                    beams.add(Beam(bird))
            # ▲ 追加機能6：弾幕発射のための処理 ▲

  

            if event.type == pg.KEYDOWN and event.key == pg.K_RSHIFT and score.value>=100: #追加機能4
                score.value=score.value-100
                bird.state="hyper"
                bird.hyper_life=500
                invisible.value=500
            
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_RETURN and score.value >= 200:
                    gravitys.add(Gravity())
                    score.value -= 200  # スコア消費
        screen.blit(bg_img, [0, 0])

        if invisible.value!=0:
            invisible.value=invisible.value-1

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        # ▼ 追加機能4：無敵状態での衝突判定変更 ▼
        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            if bird.state == "normal": # 通常状態
                bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return
            elif bird.state == "hyper": # 無敵状態
                exps.add(Explosion(bomb, 50))
                score.value += 1

        # for event in pg.event.get():
            
        
        for g in gravitys:
            for bomb in pg.sprite.spritecollide(g, bombs, True):
                exps.add(Explosion(bomb, 50))
                score.value += 1
            for emy in pg.sprite.spritecollide(g, emys, True):
                exps.add(Explosion(emy, 100))
                score.value += 10
        

        gravitys.update()
        gravitys.draw(screen)
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        if invisible.value !=0:
            invisible.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()