# pylint: disable=all
import pandas as pd

# load test dataset
# modify some values to test the model

df_test = pd.read_csv('./data/dataset.csv')

# modify MetalOutputIntensity for rows from 1020 to 1200
df_test.loc[1020:1200, 'MetalOutputIntensity'] = df_test.loc[1020:1200, 'MetalOutputIntensity'] + 2 

# save the modified dataset
df_test.to_csv('./data/dataset_test.csv', index=False)
