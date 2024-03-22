import streamlit as st
import pandas as pd
import numpy as np
import urllib.parse
import urllib.request
import json
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.font_manager as fm

st.set_page_config(layout = 'wide')

@st.cache_data
def fontRegistered():
    font_dirs = os.getcwd()
    font_files = fm.findSystemFonts(fontpaths=font_dirs)

    for font_file in font_files:
        fm.fontManager.addfont(font_file)
    fm._load_fontmanager(try_read_cache=False)


# 필요한 함수 정의
@st.cache_data
def get_location(loc, client_id, client_secret):
    url = f"https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode?query=" + urllib.parse.quote(loc)
    request = urllib.request.Request(url)
    request.add_header('X-NCP-APIGW-API-KEY-ID', client_id)
    request.add_header('X-NCP-APIGW-API-KEY', client_secret)
    response = urllib.request.urlopen(request)
    res = response.getcode()
    if res == 200:
        response_body = response.read().decode('utf-8')
        response_body = json.loads(response_body)
        if response_body['meta']['totalCount'] == 1:
            lat = response_body['addresses'][0]['y']
            lon = response_body['addresses'][0]['x']
            return (lon, lat)
        else:
            return None  # 주소가 존재하지 않으면 None 반환
    else:
        return None  # 오류 발생 시 None 반환
@st.cache_data
def get_optimal_route(start, goal, client_id, client_secret, option=''):
    if not start or not goal:  # 시작점이나 끝점이 None이면 거리 계산을 수행하지 않음
        return None
    url = f"https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving?start={start[0]},{start[1]}&goal={goal[0]},{goal[1]}&option={option}"
    request = urllib.request.Request(url)
    request.add_header('X-NCP-APIGW-API-KEY-ID', client_id)
    request.add_header('X-NCP-APIGW-API-KEY', client_secret)
    response = urllib.request.urlopen(request)
    res = response.getcode()
    if res == 200:
        response_body = response.read().decode('utf-8')
        route_data = json.loads(response_body)
        return route_data['route']['traoptimal'][0]['summary']['distance'] / 1000  # 미터를 킬로미터로 변환
    else:
        return None
    
# 각 사업자와 가장 가까운 지점을 찾는 함수
def find_closest_branch(row, distance_columns):
    min_distance = np.min(row[distance_columns])  # 최소 거리 찾기
    if np.isnan(min_distance):  # 최소 거리가 NaN이면
        return None  # 가장 가까운 지점이 없음
    for col in distance_columns:
        if row[col] == min_distance:
            return col.replace('과의 거리', '')  # '과의 거리'를 제거한 지점명 반환
    return None  # 여기에 도달하면 에러, 하지만 일반적으로 발생하지 않음



# API 사용자 정보
#client_id = '6a26v3p4lz'
#client_secret = 'ZNmfoEoLod0kQOWMzhB9NjoTR6azcJvUhxadlrwe'

def main():
    st.title('사업재기 공모 지점 배정 시스템')

    # API 사용자 정보
    client_id = st.text_input('Client ID')
    client_secret = st.text_input('Client Secret', type='password')

    # 파일 업로더
    a_data_file = st.file_uploader('지점 데이터 파일 업로드', type=['xlsx'])
    b_data_file = st.file_uploader('사업자 데이터 파일 업로드', type=['xlsx'])

    if a_data_file and b_data_file and client_id and client_secret:
        a_data = pd.read_excel(a_data_file)
        b_data = pd.read_excel(b_data_file)

        # 거리 정보 추가 및 가장 가까운 지점 계산 로직...
        for i, row in a_data.iterrows():
            branch_name = row['지점명']
            branch_location = get_location(row['주소'], client_id, client_secret)

            b_data[f'{branch_name}과의 거리'] = b_data['주소'].apply(
                lambda x: get_optimal_route(get_location(x, client_id, client_secret), branch_location, client_id, client_secret)
            )
        
        # 거리 컬럼만 필터링
        distance_columns = [col for col in b_data.columns if '과의 거리' in col]
        
        # '가장 가까운 지점' 컬럼 추가
        b_data['배정결과(가까운 기준)'] = b_data.apply(lambda row: find_closest_branch(row, distance_columns), axis=1)

        # 결과 표시
        st.dataframe(b_data)

        # 결과 다운로드
        csv = b_data.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="다운로드 (CSV)", data=csv, file_name='updated_b_data.csv', mime='text/csv')


        fontRegistered()

        col1, col2 = st.columns(2)
        # 배정 결과 시각화
        if '배정결과(가까운 기준)' in b_data.columns:
            with col1:
                st.write("### 지점별 배정된 사업자 수", b_data['배정결과(가까운 기준)'].value_counts())
            # 지점별 배정된 사업자 수 바 차트 생성

            plt.rc('font', family='Malgun Gothic')
            fig, ax = plt.subplots()
            b_data['배정결과(가까운 기준)'].value_counts().plot(kind='bar', ax=ax)
            with col2 :
                st.write("### 배정현황 시각화")
                st.pyplot(fig)

            # 지점별 배정된 사업자 리스트
            st.write("### 지점별 배정된 사업자 리스트")
            assigned_branches = b_data.groupby('배정결과(가까운 기준)')
            for branch, group in assigned_branches:
                st.write(f"#### {branch}")
                st.write(group[['사업자명', '주소']])
        else:
            st.error("지점 배정 결과를 찾을 수 없습니다.")

if __name__ == "__main__":
    main()
