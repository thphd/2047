quotes = '''
真理是时间之产物，而不是权威之产物。##弗兰西斯·培根
Nothing happens until something moves.##Albert Einstein
Whenever you feel like criticizing any one, just remember that all the people in this world haven’t had the advantages that you’ve had.##The Great Gatsby
比起法西斯，我宁愿做一只猪，猪是没有国家和法律可言的。##《红猪》
请记得那些对你好的人，因为他本可以不这样。##《千与千寻》

Peace has cost you your strength! Victory has defeated you.##The Dark Knight Rises
安逸令你虚弱，胜利麻痹了你的神经。##《黑暗骑士崛起》

Most men die at twenty or thirty; thereafter they are only reflections of themselves: for the rest of their lives they are aping themselves, repeating from day to day more and more mechanically and affectedly what they said and did and thought and loved when they were alive.##'Jean-Christophe' by Romain Rolland

灾难并不是死了两万人这样一件事，而是死了一个人这件事，发生了两万次。 ##北野武
Government is not the solution to our problem, government is the problem.##Ronald Reagan
If the facts scare you, the problem isn't with the facts.
我想在一切终结的时候，能够像一个真正的诗人那样说：我们不是懦夫，我们做完了所有能做的。##阿莱杭德娜·皮扎尼克
人生还不如波德莱尔的一行诗。##芥川龙之介
The highest activity a human being can attain is learning for understanding, because to understand is to be free. 人类可以达到的最高行为是学会理解，因为理解使人自由。##斯宾诺莎
A fronte praecipitium a tergo lupi. 悬崖在面前，狼群在背后。

Absenti nemo non nocuisse velit. 愿没有人会说不在场人的坏话。

Abusus non tollit usum. 滥用不排除好用。

Actus non facit reum nisi mens est rea. 非有意犯罪的行为不算犯罪行为。

Aliquando bonus dormitat Homerus. 有时候连好人荷马也会打瞌睡。

Happiness is a virtue, not its reward. 快乐是一种美德，而不是一种奖赏。##斯宾诺莎
Be careful what you wish for, lest it come true! 小心许愿，当心成真！##伊索寓言
'''

from forbiddenfruit import curse
curse(list, 'map', lambda self,f:list(map(f,self)))
curse(list, 'filter', lambda self,f:list(filter(f,self)))

quotes = quotes.split('\n').map(lambda l:l.strip()).filter(lambda l:len(l)>0)

quotes = quotes.map(lambda s:s.split('##')).map(lambda l:(l[0], l[1] if len(l)==2 else ''))

import random

def get_quote():
    return random.choice(quotes)

if __name__ == '__main__':
    # for i in quotes:
    #     print(get_quote())

    import json
    a = (json.dumps(quotes, ensure_ascii=False))
    print(a)
    open('quotes.txt','w',encoding='utf-8').write(a)
