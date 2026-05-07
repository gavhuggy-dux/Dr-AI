import React, { useEffect, useState, useRef } from 'react';
import { View, Image, TouchableOpacity, StyleSheet, Dimensions, Text, Linking } from 'react-native';
import { colors, borderRadius } from '../theme';
import apiClient from '../api/client';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export default function AdCarousel({ height = 120 }) {
  const [ads, setAds] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const intervalRef = useRef(null);

  useEffect(() => {
    fetchAds();
    startRotation();
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  async function fetchAds() {
    try {
      const ad = await apiClient.getNextAd();
      if (ad && ad.image_url) {
        setAds([ad]);
      }
    } catch (e) {
      console.error('Failed to fetch ad:', e);
    }
  }

  function startRotation() {
    intervalRef.current = setInterval(() => {
      fetchAds();
      setCurrentIndex(prev => {
        if (ads.length > 1) return (prev + 1) % ads.length;
        return 0;
      });
    }, 8000);
  }

  function handleAdPress(ad) {
    if (ad?.id) {
      apiClient.clickAd(ad.id).catch(() => {});
    }
    if (ad?.link_url) {
      Linking.openURL(ad.link_url).catch(() => {});
    }
  }

  if (ads.length === 0) return null;

  const ad = ads[currentIndex] || ads[0];
  if (!ad) return null;

  return (
    <View style={[styles.container, { height }]}>
      <TouchableOpacity
        style={styles.adTouchable}
        onPress={() => handleAdPress(ad)}
        activeOpacity={0.8}
      >
        <Image
          source={{ uri: ad.image_url }}
          style={styles.image}
          resizeMode="cover"
        />
        {ad.alt_text && (
          <View style={styles.overlay}>
            <Text style={styles.altText} numberOfLines={2}>{ad.alt_text}</Text>
          </View>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: SCREEN_WIDTH,
    overflow: 'hidden',
    backgroundColor: colors.card,
  },
  adTouchable: {
    flex: 1,
    position: 'relative',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  overlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    padding: 8,
  },
  altText: {
    color: colors.white,
    fontSize: 12,
  },
});
