# 控制流

## 条件判断

```python
score = 85

if score >= 90:
    grade = "优秀"
elif score >= 80:
    grade = "良好"
elif score >= 60:
    grade = "及格"
else:
    grade = "不及格"

print(grade)  # "良好"
```

## 循环

### for 循环

```python
# 遍历列表
fruits = ["苹果", "香蕉", "橘子"]
for fruit in fruits:
    print(fruit)

# 使用 range
for i in range(5):        # 0, 1, 2, 3, 4
    print(i)

for i in range(1, 10, 2): # 1, 3, 5, 7, 9
    print(i)

# 枚举遍历
for index, fruit in enumerate(fruits):
    print(f"{index}: {fruit}")
```

### while 循环

```python
count = 0
while count < 5:
    print(count)
    count += 1
```

### break 和 continue

```python
# break：跳出整个循环
for i in range(10):
    if i == 5:
        break
    print(i)  # 0, 1, 2, 3, 4

# continue：跳过当前迭代
for i in range(10):
    if i % 2 == 0:
        continue
    print(i)  # 1, 3, 5, 7, 9
```

## 列表推导式

列表推导式是 Python 创建列表的简洁方式。

```python
# 基本形式：[表达式 for 变量 in 可迭代对象 if 条件]

# 生成平方数
squares = [x**2 for x in range(10)]
# [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

# 带条件筛选
evens = [x for x in range(20) if x % 2 == 0]
# [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

# 嵌套循环
pairs = [(x, y) for x in [1, 2] for y in [3, 4]]
# [(1, 3), (1, 4), (2, 3), (2, 4)]
```
