import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import pyngrok
from vega_datasets import data as vegadatasets
# load data and preprocess
csvs = []
league_names = ['English Premier League','Spain Primera Division','Italian Serie A','German 1. Bundesliga']
for year in range(18,23):
  df = pd.read_csv(f"data/players_{year}.csv", index_col=None, header=0)
  df['Year'] = f'20{year}'
  df = df.loc[df['league_name'].isin(league_names)]
  scaler = MinMaxScaler()
  df['overall'] = scaler.fit_transform(df[['overall']])
  df.loc[df['club_name'] == 'Atlético de Madrid', 'club_name'] = 'Atlético Madrid'
  df.loc[df['club_name'] == 'Real Madrid CF', 'club_name'] = 'Real Madrid'
  df.loc[df['club_name'] == 'Real Betis Balompié', 'club_name'] = 'Real Betis'
  df.loc[df['club_name'] == 'AC Milan', 'club_name'] = 'Milan'
  csvs.append(df)
data = pd.concat(csvs, axis=0, ignore_index=True)

#prepare relevant data 
data = data[['short_name','long_name','age','Year','nationality','club_name','league_name','overall','value_eur','wage_eur','pace','dribbling']]
data['Year'] = data['Year'].astype('int')
min_year = 2018
max_year = 2022

#find best 3 clubs in each league during 2018-2022
english_data = data.loc[data['league_name'] == 'English Premier League']
spain_data = data.loc[data['league_name'] == 'Spain Primera Division']
italian_data = data.loc[data['league_name'] == 'Italian Serie A']
german_data = data.loc[data['league_name'] == 'German 1. Bundesliga']
league_df_dict = {'English Premier League':english_data,'Spain Primera Division':spain_data,'Italian Serie A':italian_data,'German 1. Bundesliga':german_data}

league_clubs = {'English Premier League':[],'Spain Primera Division':[],'Italian Serie A':[],'German 1. Bundesliga':[]}
for key in league_df_dict.keys():
  this_data = league_df_dict[key]
  name = key
  clubes_name = list(this_data.groupby(['club_name'])['overall'].mean().reset_index().sort_values(by=['overall'],ascending = False)[0:3]['club_name'])
  league_clubs[name] = clubes_name

for key in league_df_dict.keys():
  temp = league_df_dict[key]
  league_name = key
  league_df_dict[key] = temp.loc[temp['club_name'].isin(league_clubs[league_name])]

# creats deshbord + get the input from dashbord
st.set_page_config(layout="wide")
st.title("FIFA 18-22 Top 4 Leagues Visualization")
st.markdown("###")
st.markdown("### Top 3 Clubs in Each League")
st.markdown("###")
leagues = st.multiselect('League', league_names,default=[])
start_year, end_year = st.slider("Year Period", min_value=min_year, max_value=max_year, value=(min_year, max_year))
st.markdown('###')
left_column, right_column = st.columns([1,1.5])

# if the league enpty, print message 
if leagues == []:
  left_column.markdown('### *No League was selected*')

# else, create vizualuzations 
else:
  #take only selected data by league and years 
  selected_league_df = pd.concat([league_df_dict[key] for key in leagues])
  source = selected_league_df[(selected_league_df['Year'] >= start_year) & (selected_league_df['Year'] <= end_year)]
  #set consistant colors by league and club
  English_colors = ['#6CC417', '#43BFC7','#6c9da1']
  Spain_colors = ['#FAAFBA','#F75D59','#fa0505']
  Italian_colors = ['#FBB117','#C2B280','#FFFF33']
  German_colors = ['#F433FF','#915F6D','#D291BC']
  all_clubs_to_zip = league_clubs['English Premier League']+league_clubs['Spain Primera Division']+league_clubs['Italian Serie A']+league_clubs['German 1. Bundesliga']
  all_colors_to_zip = English_colors+Spain_colors+Italian_colors+German_colors
  colors_dict  = dict(zip(all_clubs_to_zip, all_colors_to_zip))
  source_clubs = source['club_name'].unique()
  source_clubs_colors = [colors_dict[club] for club in source_clubs]
  defult_scale = alt.Scale(domain=source_clubs, range=source_clubs_colors)

  #left column - scatter plot with bars plot below

  lc_base = alt.Chart(source).properties(height=380)
  brush = alt.selection(type='interval')

  lc_points = lc_base.mark_point().encode(
      y= alt.Y('wage_eur', axis=alt.Axis(title='Weekly Wage (€)',titleFontSize=16,labelFontSize=12)),
      x= alt.X('overall', axis=alt.Axis(title='Normalized Overall Score',titleFontSize=16,labelFontSize=12)),
      color=alt.condition(brush,alt.Color('club_name:N',scale = defult_scale, title='Club Name'), alt.value('lightgray')),
      tooltip=[alt.Tooltip('short_name:N', title='Name'),alt.Tooltip('Year:Q', title='Year')]).add_selection(brush)

  max_len_bar = max([len(source[source['club_name']==club]) for club in source['club_name'].unique()])
  
  lc_bars = lc_base.mark_bar().encode(
      y=alt.Y('club_name:N',sort='-x', axis=alt.Axis(title='Club Name',titleFontSize=16,labelFontSize=12)),
      color = 'club_name',
      x=alt.X('count(club_name)',scale=alt.Scale(domain=[0, max_len_bar]), axis=alt.Axis(title='Player Count',titleFontSize=16,labelFontSize=12))
  ).transform_filter(brush)

  lc_text = lc_bars.mark_text(
    align='left',
    baseline='middle',dx=3).encode(text='count(club_name):Q')
  
  chart_titel = f'{start_year} - {end_year}' if start_year != end_year else f'{start_year}'
  left_column.markdown(f'#####  Overall Score Vs. Weekly Wage at ({chart_titel})') 
  left_column.altair_chart(lc_points & (lc_bars+ lc_text).properties(height=900), use_container_width=True)



  #right column - map , performance histogram
  ##upper row - MAP 
  # data preprocess - get the lon and lat from csv, join, groupby country then count players by country
  data_copy = source.copy()
  locations = pd.read_csv("data/locations.csv", index_col=None, header=0)
  locations = locations[['latitude','longitude','country']]
  data_copy.rename(columns = {'nationality':'country'}, inplace = True)
  locations['country'] = locations['country'].str.upper()
  data_copy['country'] = data_copy['country'].str.upper()
  data_copy = data_copy.join(locations.set_index('country'), on='country')
  counts = pd.DataFrame(data_copy.groupby(['country']).agg({"short_name": "nunique"}))
  avg_loc = data_copy.groupby(['country'])['latitude','longitude'].mean()
  agg_data = avg_loc.join(counts)
  agg_data.rename(columns = {'short_name':'num_players'}, inplace = True)
  agg_data.reset_index(inplace=True)
  agg_data.dropna(inplace=True)
  def bucket(row):
    for i in range(0,2000,10):
      if row['num_players'] < i:
        return i
  agg_data['players_num_bucket'] = agg_data.apply(lambda row:bucket(row),axis=1)

  #plot world map with points
  sourcemap = alt.topo_feature(vegadatasets.world_110m.url, 'countries')
  source_on_map = agg_data

  rcu_base = alt.Chart(sourcemap).mark_geoshape(
    fill='darkgray',
    stroke='gray').properties(
    width=980,
    height=500)

  projections = ['equirectangular', 'mercator', 'orthographic', 'gnomonic']
  rcu_charts = rcu_base.project('equirectangular')

  rcu_points = alt.Chart(source_on_map).mark_circle().encode(
      longitude='longitude:Q',
      latitude='latitude:Q',
      color=alt.Color('players_num_bucket', scale=alt.Scale(scheme='goldorange'), title ='Number of Players', 
                      legend = alt.Legend(orient = 'none',labelFontSize=14,titleFontSize=16,
                                          legendX=40, legendY=350, direction='horizontal', titleAnchor='middle')),
      size=alt.Size('players_num_bucket'),
      tooltip=[alt.Tooltip('country:N', title='Natiounality'),alt.Tooltip('num_players:Q', title='Count')]
      ).properties(title=f'Total Number of Players in Each Natiounality at ({chart_titel})')
      
  with right_column:
    interactive_map = rcu_charts + rcu_points
    st.write(interactive_map.configure_title(fontSize=20))

  ##lower row - age histogram linked to performences scatter plot 
  performences_data = source.copy()[['age','Year','club_name','league_name','pace','dribbling']]
  performences_data.dropna(inplace=True)
  performences_data['pace'] = scaler.fit_transform(performences_data[['pace']])
  performences_data['dribbling'] = scaler.fit_transform(performences_data[['dribbling']])

  rcl_selector = alt.selection_single(empty='all', fields=['club_name'])
  
  rcl_base = alt.Chart(performences_data).properties(
      width=350,
      height=330).add_selection(rcl_selector)

  rcl_points = rcl_base.mark_point(filled=True, size=300).encode(
      y=alt.Y('mean(dribbling):Q',scale=alt.Scale(domain=[0.35,1]),axis=alt.Axis(title='Normalized Mean Dribbling Score',titleFontSize=16,labelFontSize=12)),
      x=alt.X('mean(pace):Q',scale=alt.Scale(domain=[0.35,1]),axis=alt.Axis(title='Normalized Mean Pace Score',titleFontSize=16,labelFontSize=12)),
      color=alt.condition(rcl_selector,
                           alt.Color('club_name:N',scale = defult_scale),
                          alt.value('lightgray')),
    tooltip=[alt.Tooltip('club_name:N', title='Club Name')]).properties(title=f'Mean Pace Score Vs. Mean Dribbling Score By Club at ({chart_titel})')

  rcl_hists = rcl_base.mark_bar(opacity=0.5, thickness=150).encode(
      x=alt.X('age',bin=alt.Bin(step=3),axis=alt.Axis(title='Age',titleFontSize=16,labelFontSize=12)),
      y=alt.Y('count()',stack=None,axis=alt.Axis(title='Player Count',titleFontSize=16,labelFontSize=12)),
      color=alt.Color('club_name:N',scale=defult_scale,title='Club Name')).transform_filter(rcl_selector).properties(title=f'Players Age Distribution at ({chart_titel})')

  with right_column:
    interactive_body_chart = rcl_points | rcl_hists
    st.write(interactive_body_chart.configure_title(fontSize=15))
