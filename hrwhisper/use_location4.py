# -*- coding: utf-8 -*-
# @Date    : 2017/10/23
# @Author  : hrwhisper
"""
    加上和各个店铺的距离,反而下下降了
"""

from math import sin, cos, atan2, sqrt, pi

import gpxpy.geo
from scipy.sparse import csr_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.externals import joblib

from common_helper import ModelBase, XXToVec
from parse_data import read_mall_data, read_train_join_mall
from use_wifi import WifiToVec


def get_distance_by_latitude_and_longitude(lat1, lon1, lat2, lon2):
    return gpxpy.geo.haversine_distance(lat1, lon1, lat2, lon2)


def center_latitudes_and_longitudes(geo_coordinates):
    """

    :param geo_coordinates: [[latitude,longtitude],...]
    :return: [latitude,longitudes]
    """
    x = y = z = 0
    for (lat, lng) in geo_coordinates:
        lat, lng = lat * pi / 180, lng * pi / 180
        x += cos(lat) * cos(lng)
        y += cos(lat) * sin(lng)
        z += sin(lat)

    x = x / len(geo_coordinates)
    y = y / len(geo_coordinates)
    z = z / len(geo_coordinates)
    lng = atan2(y, x)
    hyp = sqrt(x ** 2 + y ** 2)
    lat = atan2(z, hyp)
    return lat * 180 / pi, lng * 180 / pi


def shop_location():
    mall = read_mall_data()
    mall = mall[['shop_id', 'longitude', 'latitude']]


class LocationToVec4(XXToVec):
    MALL = read_mall_data()

    def __init__(self):
        super().__init__('./feature_save/location_features_{}_{}.pkl', './feature_save/location_features_{}.pkl')
        self.scale = 10

    def _location_to_vec(self, train_data, mall_id):
        train_data = train_data[train_data['mall_id'] == mall_id]
        mall = self.MALL[self.MALL['mall_id'] == mall_id]
        mall = mall.sort_values(by='shop_id')
        indptr = [0]
        indices = []
        data = []
        for log, lat in zip(train_data['longitude'], train_data['latitude']):
            indices.extend([0, 1])
            data.extend([log * self.scale, lat * self.scale])
            for i, (s_log, s_lat) in enumerate(zip(mall['longitude'], mall['latitude']), 2):
                indices.append(i)
                data.append(get_distance_by_latitude_and_longitude(lat, log, s_lat, s_log))
            indptr.append(len(indices))

        return csr_matrix((data, indices, indptr))

    def train_data_to_vec(self, train_data, mall_id, renew=True, should_save=False):
        """
        :param train_data: pandas. train_data.join(mall_data.set_index('shop_id'), on='shop_id', rsuffix='_mall')
        :param mall_id: str
        :param renew: renew the feature
        :param should_save: bool, should save the feature on disk or not.
        :return: csr_matrix
        """
        if renew:

            features = self._location_to_vec(train_data, mall_id)
            if should_save:
                joblib.dump(features, self.FEATURE_SAVE_PATH.format('train', mall_id))
        else:
            features = joblib.load(self.FEATURE_SAVE_PATH.format('train', mall_id))
        return features

    def test_data_to_vec(self, test_data, mall_id, renew=True, should_save=False):
        if renew:
            features = self._location_to_vec(test_data, mall_id)
            if should_save:
                joblib.dump(features, self.FEATURE_SAVE_PATH.format('test', mall_id))
        else:
            features = joblib.load(self.FEATURE_SAVE_PATH.format('test', mall_id))
        return features


class UseLoc(ModelBase):
    def __init__(self):
        super().__init__()

    def _get_classifiers(self):
        return {
            'random forest': RandomForestClassifier(n_jobs=3, n_estimators=200, random_state=self._random_state,
                                                    class_weight='balanced'),
        }


def train_test():
    task = UseLoc()
    task.train_test([LocationToVec4(), WifiToVec()])
    # task.train_and_on_test_data([WifiToVec()])


if __name__ == '__main__':
    train_test()
    # LocationToVec4()._location_to_vec(read_train_join_mall(), 'm_6803')