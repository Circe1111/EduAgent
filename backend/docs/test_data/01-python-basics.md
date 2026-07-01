# Python 基础语法

## 变量与数据类型

Python 是动态类型语言，变量不需要声明类型。

```python
# 基本数据类型
name = "Alice"        # 字符串 str
age = 20              # 整数 int
height = 1.68         # 浮点数 float
is_student = True     # 布尔值 bool

# 类型转换
age_str = str(age)    # "20"
height_int = int(height)  # 1
```

## 字符串操作

```python
s = "Hello, Python"
print(len(s))          # 13
print(s.upper())       # "HELLO, PYTHON"
print(s.split(","))    # ["Hello", " Python"]
print(s[0:5])          # "Hello"（切片）
```

## 列表

```python
fruits = ["苹果", "香蕉", "橘子"]
fruits.append("葡萄")        # 添加元素
fruits.remove("香蕉")        # 删除元素
print(fruits[0])             # "苹果"
print(len(fruits))           # 3

# 列表切片
numbers = [0, 1, 2, 3, 4, 5]
print(numbers[1:4])   # [1, 2, 3]
print(numbers[::-1])  # [5, 4, 3, 2, 1, 0]（反转）
```

## 字典

```python
student = {
    "name": "张三",
    "age": 20,
    "score": 85.5
}
print(student["name"])        # "张三"
student["grade"] = "二年级"    # 添加键值对

# 遍历字典
for key, value in student.items():
    print(f"{key}: {value}")
```
