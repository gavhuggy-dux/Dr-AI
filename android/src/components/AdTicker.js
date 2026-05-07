import React, { useEffect, useRef, useState } from 'react';
import { View, Text, Animated, StyleSheet } from 'react-native';
import { colors } from '../theme';
import apiClient from '../api/client';

export default function AdTicker() {
  const [tickers, setTickers] = useState([
    'Welcome to Dr. AI — Your 24/7 Health Assistant',
    'Consult with AI-powered medical intelligence',
    'Your health records, always accessible',
  ]);
  const scrollAnim = useRef(new Animated.Value(0)).current;
  const currentIndex = useRef(0);

  useEffect(() => {
    fetchTickers();
    startScrolling();
  }, []);

  async function fetchTickers() {
    try {
      const data = await apiClient.getAdTickers();
      if (Array.isArray(data) && data.length > 0) {
        setTickers(data.map(t => typeof t === 'object' ? t.text : t));
      }
    } catch (e) {
      // Use defaults
    }
  }

  function startScrolling() {
    const loop = () => {
      Animated.sequence([
        Animated.timing(scrollAnim, {
          toValue: -200,
          duration: 4000,
          useNativeDriver: true,
        }),
        Animated.timing(scrollAnim, {
          toValue: 0,
          duration: 0,
          useNativeDriver: true,
        }),
      ]).start(() => {
        currentIndex.current = (currentIndex.current + 1) % tickers.length;
        loop();
      });
    };
    loop();
  }

  const currentText = tickers[currentIndex.current] || tickers[0];

  return (
    <View style={styles.container}>
      <Animated.Text
        style={[
          styles.text,
          { transform: [{ translateX: scrollAnim }] },
        ]}
        numberOfLines={1}
      >
        {currentText}
      </Animated.Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.card,
    paddingVertical: 6,
    paddingHorizontal: 12,
    overflow: 'hidden',
    borderBottomWidth: 1,
    borderBottomColor: colors.cardBorder,
  },
  text: {
    color: colors.accent,
    fontSize: 12,
    fontWeight: '500',
  },
});
