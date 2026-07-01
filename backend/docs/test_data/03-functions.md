# 函数

## 函数定义与调用

```python
def greet(name):
    """向指定的人打招呼"""
    return f"你好，{name}！"

print(greet("小明"))  # "你好，小明！"
```

## 参数类型

```python
# 位置参数
def add(a, b):
    return a + b

# 默认参数
def power(base, exp=2):
    return base ** exp

print(power(3))      # 9
print(power(3, 3))   # 27

# 关键字参数
def introduce(name, age, city):
    print(f"{name}，{age}岁，来自{city}")

introduce(age=20, city="北京", name="小红")

# 可变参数
def sum_all(*args):
    return sum(args)

print(sum_all(1, 2, 3, 4, 5))  # 15

# 关键字可变参数
def print_info(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")
```

## 返回值

```python
def analyze_numbers(numbers):
    """返回多个统计结果"""
    total = sum(numbers)
    avg = total / len(numbers)
    maximum = max(numbers)
    minimum = min(numbers)
    return total, avg, maximum, minimum

t, a, mx, mn = analyze_numbers([1, 2, 3, 4, 5])
print(f"总和={t}, 平均={a}, 最大={mx}, 最小={mn}")
```

## 作用域

```python
x = 10  # 全局变量

def func():
    x = 20  # 局部变量，不影响全局
    print(x)

func()      # 20
print(x)    # 10

def modify_global():
    global x
    x = 30  # 修改全局变量

modify_global()
print(x)    # 30
```

## 匿名函数 (lambda)

```python
# lambda 参数: 表达式
square = lambda x: x ** 2
print(square(5))  # 25

# 配合 map/filter/sorted
numbers = [1, 2, 3, 4, 5]
doubled = list(map(lambda x: x * 2, numbers))
print(doubled)  # [2, 4, 6, 8, 10]

evens = list(filter(lambda x: x % 2 == 0, numbers))
print(evens)  # [2, 4]
```
