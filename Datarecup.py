import pandas as pd

df = pd.read_csv("ref/ref/sup_exploitant.txt", sep=";")
print(df.head())
print(df.info())
print(df.describe())