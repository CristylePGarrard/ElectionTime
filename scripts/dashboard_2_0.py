# -*- coding: utf-8 -*-
"""dashboard_2.0.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1qzPz3CjWi3Q35hFWyAcdUlN775X_9GQ3
"""

# ####### Install necessary libraries ####### #
# !pip install pandas dash plotly openpyxl

# import dash
# from dash import dcc, html, Input, Output
# import dash_table
import pandas as pd
# import plotly.express as px

# ####### Mount Google Drive to Colab ####### #
from google.colab import drive
drive.mount('/content/drive')

# ####### Set the file path to uploaded Excel file ####### #
# Update the path with the actual location of file in Google Drive
file_path = '/content/drive/My Drive/ut_pol/'
filename = 'cleaned_candidates_data.csv'

# Load your cleaned data into a DataFrame
df = pd.read_csv(file_path+filename)

print(df.columns)

# Columns to keep in the table
columns_to_display = ['Name on Ballot', 'Office', 'District', 'Party', 'Status', 'Display District', 'Incumbent']

df = df[columns_to_display].copy().reset_index(drop=True)
print(df.info())

import plotly.express as px

# Group by 'Office' and 'Party', and count the number of occurrences for each 'Name on Ballot'
office_party_group = df.groupby(['Office', 'Party']).agg({'Name on Ballot': 'count'}).reset_index()

# Create a bar chart to visualize the counts of candidates by office and party
fig = px.bar(
    office_party_group,
    x='Office',
    y='Name on Ballot',
    color='Party',
    title='Number of All Candidates by Office and Party',
    labels={'Name on Ballot': 'Count of Candidates'},
    barmode='stack'
)

# Show the chart
fig.show()

# I only want candidates that will be on the ballot
include_status = ['Election Candidate','Write-In']

df = df[df['Status'].isin(include_status)].copy().reset_index(drop=True)

# Create a bar chart to visualize the counts of candidates by office and party
fig = px.bar(
    df.groupby(['Office', 'Party']).agg({'Name on Ballot': 'count'}).reset_index(),
    x='Office',
    y='Name on Ballot',
    color='Party',
    title='Number of Candidates on the Ballot by Office and Party',
    labels={'Name on Ballot': 'Count of Candidates'},
    barmode='stack'
)

# Show the chart
fig.show()

# Create a df for judges and justices and remove from main dataframe
# They are a different type of candidate and also aren't a part of a political party
judges_df = df.loc[df['Party']== 'NO PARTY'].copy().reset_index(drop=True)

fig = px.bar(
    judges_df.groupby(['Office']).agg({'Name on Ballot': 'count'}).reset_index(),
    x='Office',
    y='Name on Ballot',
    color='Office',
    title='Number of Judges by Office',
    labels={'Name on Ballot': 'Count of Candidates'}
)

# Show the chart
fig.show()

# remove judges from df
df = df.loc[~df['Party'].isnull()].copy().reset_index(drop=True)

fig = px.bar(
    df.groupby(['Office', 'Party']).agg({'Name on Ballot': 'count'}).reset_index(),
    x='Office',
    y='Name on Ballot',
    color='Party',
    title='Number of Candidates by Office and Party',
    labels={'Name on Ballot': 'Count of Candidates'},
    barmode='stack'
)

# Show the chart
fig.show()

# Some of the candidates everyone votes for and others depend on the districts that they are a part of.
# Let's separate them into two dataframes

statewide_candidates = df.loc[df['District'] == '0'].copy().reset_index(drop=True)

fig = px.bar(
    statewide_candidates.groupby(['Office', 'Party']).agg({'Name on Ballot': 'count'}).reset_index(),
    x='Office',
    y='Name on Ballot',
    color='Party',
    title='Number of Statewide Candidates by Office and Party',
    labels={'Name on Ballot': 'Count of Candidates'},
    barmode='stack'
)

# Show the chart
fig.show()

district_candidates = df.loc[df['District'] != '0'].copy().reset_index(drop=True)

fig = px.bar(
    district_candidates.groupby(['Office', 'Party']).agg({'Name on Ballot': 'count'}).reset_index(),
    x='Office',
    y='Name on Ballot',
    color='Party',
    title='Number of District Candidates by Office and Party',
    labels={'Name on Ballot': 'Count of Candidates'},
    barmode='stack'
)

# Show the chart
fig.show()

# let's breakdown each office by district

for office in district_candidates['Office'].unique():
    print(office)

    # Create a filtered DataFrame for the current office
    office_df = district_candidates.loc[district_candidates['Office'] == office]

    # Group by District and Party to get the count of 'Name on Ballot'
    # Also join with the original dataframe to get the names
    office_grouped = office_df.groupby(['District', 'Party'])\
                              .agg({'Name on Ballot': 'count'})\
                              .reset_index()

    # Concatenate candidate names into a single string for display
    office_grouped = office_grouped.merge(
        office_df.groupby(['District', 'Party'])['Name on Ballot']
                .apply(lambda x: ', '.join(x)).reset_index(name='Candidate Names'),
        on=['District', 'Party']
    )

    # Create the bar chart
    fig = px.bar(
        office_grouped,
        x='District',
        y='Name on Ballot',
        color='Party',
        text='Candidate Names',  # Show candidate names on the bars
        title=f'{office} Candidates by District and Party',  # Update the title with office name
        labels={'Name on Ballot': 'Count of Candidates'},
        barmode='stack'
    )

    # Update the text position and style for clarity
    fig.update_traces(
        textposition='inside',
        textangle=0,
        textfont_size=10,
        # texttemplate'%{text}',
        insidetextanchor='middle')

    # Show the chart
    fig.show()

# why aren't the districts sorted???
district_candidates['District'] = pd.to_numeric(district_candidates['District'], errors='coerce')

# Sort the DataFrame by the 'District' column
district_candidates = district_candidates.sort_values(by='District').reset_index(drop=True)

print(district_candidates.head())

import plotly.express as px

# Define a custom color mapping for the parties
party_colors = {
    'Republican': 'red',
    'Democratic': 'blue',
    'Independent': 'green',
    'Libertarian': 'purple',
    'Other': 'gray'
}

# Loop through unique offices in the district_candidates dataframe
for office in district_candidates['Office'].unique():

    # Exclude "Judge" and "Justice" from the loop
    if office in ["Judge", "Justice"]:
        continue  # Skip these offices

    print(office)

    # Filter for the specific office
    office_df = district_candidates.loc[district_candidates['Office'] == office]

    # Group by District and Party to get the count of 'Name on Ballot'
    office_grouped = office_df.groupby(['District', 'Party'])\
                              .agg({'Name on Ballot': 'count'})\
                              .reset_index()

    # Concatenate candidate names into a single string for display
    office_grouped = office_grouped.merge(
        office_df.groupby(['District', 'Party'])['Name on Ballot']
                .apply(lambda x: ', '.join(x)).reset_index(name='Candidate Names'),
        on=['District', 'Party']
    )

    # Filter out districts with no candidates
    office_grouped = office_grouped[office_grouped['Name on Ballot'] > 0]

    # Convert 'District' to integer and then to string without decimals
    office_grouped['District'] = office_grouped['District'].astype(int).astype(str)

    # Create the bar chart with custom colors
    fig = px.bar(
        office_grouped,
        x='District',
        y='Name on Ballot',
        color='Party',
        text='Candidate Names',  # Show candidate names on the bars
        title=f'{office} Candidates by District and Party',  # Update the title with office name
        labels={'Name on Ballot': 'Count of Candidates'},
        barmode='stack',
        color_discrete_map=party_colors  # Apply the custom color mapping
    )

    # Update the text position and style for clarity
    fig.update_traces(
        textposition='inside',
        textangle=0,
        textfont_size=10,
        insidetextanchor='middle'
    )

    # Customize the x-axis so it only shows non-empty districts, without decimals
    fig.update_layout(xaxis={'type': 'category'})

    # Show the chart
    fig.show()