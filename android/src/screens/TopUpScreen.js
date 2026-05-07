import React, { useEffect, useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  ActivityIndicator, Alert, Linking,
} from 'react-native';
import { colors, borderRadius } from '../theme';
import apiClient from '../api/client';

export default function TopUpScreen({ navigation }) {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);

  useEffect(() => {
    loadPackages();
  }, []);

  async function loadPackages() {
    setLoading(true);
    try {
      const data = await apiClient.getCreditPackages();
      if (Array.isArray(data)) {
        setPackages(data);
      }
    } catch (e) {
      // Use fallback packages
      setPackages([
        { id: 1, name: 'Starter', credits: 50, price: 4.99 },
        { id: 2, name: 'Basic', credits: 200, price: 14.99 },
        { id: 3, name: 'Plus', credits: 500, price: 29.99 },
        { id: 4, name: 'Premium', credits: 1200, price: 59.99 },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handlePurchase(pkg) {
    setPurchasing(pkg.id);
    try {
      const data = await apiClient.createCheckoutSession(pkg.id);
      if (data.url) {
        await Linking.openURL(data.url);
      }
    } catch (e) {
      Alert.alert('Purchase Failed', e.message);
    } finally {
      setPurchasing(null);
    }
  }

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Top Up Credits</Text>
      <Text style={styles.subtitle}>
        Purchase credit packages to continue consulting with Dr. AI
      </Text>

      {packages.map((pkg) => (
        <View key={pkg.id} style={styles.packageCard}>
          <View style={styles.packageInfo}>
            <View style={styles.packageHeader}>
              <Text style={styles.packageName}>{pkg.name}</Text>
              <Text style={styles.packageCredits}>{pkg.credits} credits</Text>
            </View>
            <Text style={styles.packagePrice}>${(pkg.price || 0).toFixed(2)}</Text>
            {pkg.price_per_credit && (
              <Text style={styles.perCredit}>
                ${pkg.price_per_credit.toFixed(2)}/credit
              </Text>
            )}
          </View>
          <TouchableOpacity
            style={[styles.buyButton, purchasing === pkg.id && styles.buyButtonDisabled]}
            onPress={() => handlePurchase(pkg)}
            disabled={purchasing === pkg.id}
          >
            {purchasing === pkg.id ? (
              <ActivityIndicator color={colors.background} size="small" />
            ) : (
              <Text style={styles.buyButtonText}>Buy with Stripe</Text>
            )}
          </TouchableOpacity>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.white,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: 24,
    lineHeight: 20,
  },
  packageCard: {
    backgroundColor: colors.card,
    borderRadius: borderRadius.lg,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  packageInfo: {
    marginBottom: 16,
  },
  packageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  packageName: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.white,
  },
  packageCredits: {
    fontSize: 14,
    color: colors.accent,
    fontWeight: '600',
  },
  packagePrice: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.text,
    marginTop: 2,
  },
  perCredit: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  buyButton: {
    backgroundColor: colors.accent,
    borderRadius: borderRadius.md,
    paddingVertical: 14,
    alignItems: 'center',
  },
  buyButtonDisabled: {
    opacity: 0.6,
  },
  buyButtonText: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.background,
  },
});
