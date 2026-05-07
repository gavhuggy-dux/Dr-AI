import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  RefreshControl, Animated, Dimensions,
} from 'react-native';
import { colors, borderRadius, spacing } from '../theme';
import apiClient from '../api/client';
import AdTicker from '../components/AdTicker';
import AdCarousel from '../components/AdCarousel';
import { useAuth } from '../context/AuthContext';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export default function DashboardScreen({ navigation }) {
  const { user, refreshUser } = useAuth();
  const [credits, setCredits] = useState(null);
  const [onboardingProgress, setOnboardingProgress] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const progressAnim = React.useRef(new Animated.Value(0)).current;

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    Animated.timing(progressAnim, {
      toValue: onboardingProgress / 100,
      duration: 800,
      useNativeDriver: false,
    }).start();
  }, [onboardingProgress]);

  async function loadData() {
    try {
      const [balanceData, progressData] = await Promise.all([
        apiClient.getCreditBalance().catch(() => ({ balance: 0 })),
        apiClient.getOnboardingProgress().catch(() => ({ progress: 0 })),
      ]);
      setCredits(balanceData.balance ?? 0);
      setOnboardingProgress(progressData.progress ?? 0);
    } catch (e) {
      console.error('Dashboard load error:', e);
    }
  }

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([loadData(), refreshUser()]);
    setRefreshing(false);
  }, []);

  const quickActions = [
    {
      title: 'Add Medical Records',
      icon: '📄',
      color: '#4a9eff',
      onPress: () => navigation.navigate('MedicalRecords'),
    },
    {
      title: 'Book Appointment',
      icon: '📅',
      color: '#51cf66',
      onPress: () => navigation.navigate('BookAppointment'),
    },
    {
      title: 'Top Up Credits',
      icon: '💰',
      color: '#ffd43b',
      onPress: () => navigation.navigate('TopUp'),
    },
    {
      title: 'View My Health',
      icon: '❤️',
      color: '#ff6b6b',
      onPress: () => navigation.navigate('MyHealth'),
    },
  ];

  const progressWidth = progressAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <View style={styles.container}>
      <AdTicker />
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.accent}
            colors={[colors.accent]}
          />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>
              Hello{user?.first_name ? `, ${user.first_name}` : ''}
            </Text>
            <Text style={styles.headerSub}>Welcome to Dr. AI</Text>
          </View>
          <TouchableOpacity
            style={styles.settingsBtn}
            onPress={() => navigation.navigate('Settings')}
          >
            <Text style={styles.settingsIcon}>⚙️</Text>
          </TouchableOpacity>
        </View>

        {/* Credit Balance Card */}
        <TouchableOpacity
          style={styles.creditCard}
          onPress={() => navigation.navigate('TopUp')}
        >
          <View style={styles.creditRow}>
            <Text style={styles.creditLabel}>Credit Balance</Text>
            <Text style={styles.creditAmount}>{credits ?? '...'}</Text>
          </View>
          <Text style={styles.creditHint}>Tap to top up</Text>
        </TouchableOpacity>

        {/* Onboarding Progress */}
        <View style={styles.progressCard}>
          <View style={styles.progressHeader}>
            <Text style={styles.progressTitle}>Health Profile</Text>
            <Text style={styles.progressPercent}>{Math.round(onboardingProgress)}%</Text>
          </View>
          <View style={styles.progressBarBg}>
            <Animated.View
              style={[
                styles.progressBarFill,
                { width: progressWidth },
              ]}
            />
          </View>
          <TouchableOpacity onPress={() => navigation.navigate('MyHealth')}>
            <Text style={styles.progressLink}>
              {onboardingProgress < 100
                ? 'Complete your health profile →'
                : 'View your health data →'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Quick Actions */}
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <View style={styles.actionsGrid}>
          {quickActions.map((action, index) => (
            <TouchableOpacity
              key={index}
              style={styles.actionCard}
              onPress={action.onPress}
            >
              <View style={[styles.actionIcon, { backgroundColor: action.color + '20' }]}>
                <Text style={styles.actionIconText}>{action.icon}</Text>
              </View>
              <Text style={styles.actionTitle}>{action.title}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Appointments Quick View */}
        <TouchableOpacity
          style={styles.quickLink}
          onPress={() => navigation.navigate('Appointments')}
        >
          <Text style={styles.quickLinkText}>View My Appointments →</Text>
        </TouchableOpacity>

        {/* Ad Carousel at bottom */}
        <View style={styles.adContainer}>
          <AdCarousel height={100} />
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    paddingBottom: 30,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 10,
  },
  greeting: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.white,
  },
  headerSub: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 2,
  },
  settingsBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.card,
    justifyContent: 'center',
    alignItems: 'center',
  },
  settingsIcon: {
    fontSize: 22,
  },
  creditCard: {
    marginHorizontal: 20,
    backgroundColor: colors.card,
    borderRadius: borderRadius.lg,
    padding: 20,
    borderWidth: 1,
    borderColor: colors.accent + '30',
    marginTop: 10,
  },
  creditRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  creditLabel: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  creditAmount: {
    fontSize: 32,
    fontWeight: '700',
    color: colors.accent,
  },
  creditHint: {
    fontSize: 12,
    color: colors.accent,
    marginTop: 4,
    opacity: 0.7,
  },
  progressCard: {
    marginHorizontal: 20,
    backgroundColor: colors.card,
    borderRadius: borderRadius.lg,
    padding: 20,
    marginTop: 16,
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  progressTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
  },
  progressPercent: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.accent,
  },
  progressBarBg: {
    height: 8,
    backgroundColor: colors.inputBg,
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: colors.accent,
    borderRadius: 4,
  },
  progressLink: {
    fontSize: 13,
    color: colors.accent,
    marginTop: 10,
    fontWeight: '500',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.white,
    paddingHorizontal: 20,
    marginTop: 24,
    marginBottom: 12,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 16,
    gap: 12,
  },
  actionCard: {
    width: (SCREEN_WIDTH - 44) / 2,
    backgroundColor: colors.card,
    borderRadius: borderRadius.md,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  actionIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  actionIconText: {
    fontSize: 22,
  },
  actionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.text,
  },
  quickLink: {
    marginHorizontal: 20,
    marginTop: 16,
    paddingVertical: 14,
    paddingHorizontal: 20,
    backgroundColor: colors.card,
    borderRadius: borderRadius.md,
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  quickLinkText: {
    fontSize: 14,
    color: colors.accent,
    fontWeight: '500',
  },
  adContainer: {
    marginTop: 20,
    alignItems: 'center',
  },
});
