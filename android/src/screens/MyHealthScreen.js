import React, { useEffect, useState, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, Animated, ActivityIndicator, Alert,
} from 'react-native';
import { colors, borderRadius } from '../theme';
import apiClient from '../api/client';

const SECTIONS = [
  { key: 'personal', label: 'Personal Info', icon: '👤' },
  { key: 'medical_history', label: 'Medical History', icon: '📋' },
  { key: 'allergies', label: 'Allergies', icon: '⚠️' },
  { key: 'medications', label: 'Medications', icon: '💊' },
  { key: 'vitals', label: 'Vitals', icon: '❤️' },
];

export default function MyHealthScreen({ navigation }) {
  const [activeSection, setActiveSection] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [progress, setProgress] = useState(0);
  const progressAnim = useRef(new Animated.Value(0)).current;
  const [profile, setProfile] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    date_of_birth: '',
    medical_history: '',
    allergies: '',
    medications: '',
    blood_type: '',
    height_cm: '',
    weight_kg: '',
    blood_pressure_sys: '',
    blood_pressure_dia: '',
    heart_rate: '',
  });

  useEffect(() => {
    loadProfile();
  }, []);

  useEffect(() => {
    Animated.timing(progressAnim, {
      toValue: progress / 100,
      duration: 600,
      useNativeDriver: false,
    }).start();
  }, [progress]);

  async function loadProfile() {
    setLoading(true);
    try {
      const data = await apiClient.getProfile();
      if (data) {
        setProfile(prev => ({
          ...prev,
          first_name: data.first_name || '',
          last_name: data.last_name || '',
          email: data.email || '',
          phone: data.phone || '',
          date_of_birth: data.date_of_birth || '',
          medical_history: data.medical_history || '',
          allergies: data.allergies || '',
          medications: data.medications || '',
          blood_type: data.blood_type || '',
          height_cm: data.height_cm ? String(data.height_cm) : '',
          weight_kg: data.weight_kg ? String(data.weight_kg) : '',
          blood_pressure_sys: data.blood_pressure_sys ? String(data.blood_pressure_sys) : '',
          blood_pressure_dia: data.blood_pressure_dia ? String(data.blood_pressure_dia) : '',
          heart_rate: data.heart_rate ? String(data.heart_rate) : '',
        }));
      }
      const progData = await apiClient.getOnboardingProgress();
      setProgress(progData.progress ?? 0);
    } catch (e) {
      console.error('Failed to load profile:', e);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      const updateData = {};
      const section = SECTIONS[activeSection];
      switch (section.key) {
        case 'personal':
          updateData.first_name = profile.first_name;
          updateData.last_name = profile.last_name;
          updateData.phone = profile.phone;
          updateData.date_of_birth = profile.date_of_birth;
          break;
        case 'medical_history':
          updateData.medical_history = profile.medical_history;
          break;
        case 'allergies':
          updateData.allergies = profile.allergies;
          updateData.blood_type = profile.blood_type;
          break;
        case 'medications':
          updateData.medications = profile.medications;
          break;
        case 'vitals':
          updateData.height_cm = profile.height_cm ? parseFloat(profile.height_cm) : null;
          updateData.weight_kg = profile.weight_kg ? parseFloat(profile.weight_kg) : null;
          updateData.blood_pressure_sys = profile.blood_pressure_sys ? parseInt(profile.blood_pressure_sys) : null;
          updateData.blood_pressure_dia = profile.blood_pressure_dia ? parseInt(profile.blood_pressure_dia) : null;
          updateData.heart_rate = profile.heart_rate ? parseInt(profile.heart_rate) : null;
          break;
      }
      await apiClient.updateProfile(updateData);
      const progData = await apiClient.getOnboardingProgress();
      setProgress(progData.progress ?? 0);
      Alert.alert('Saved', 'Health information updated successfully');
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setSaving(false);
    }
  }

  function renderSectionContent() {
    const section = SECTIONS[activeSection];
    switch (section.key) {
      case 'personal':
        return (
          <View style={styles.section}>
            <View style={styles.fieldRow}>
              <View style={styles.halfField}>
                <Text style={styles.fieldLabel}>First Name</Text>
                <TextInput style={styles.fieldInput} value={profile.first_name} onChangeText={v => setProfile(p => ({ ...p, first_name: v }))} placeholderTextColor={colors.textSecondary} placeholder="First name" />
              </View>
              <View style={styles.halfField}>
                <Text style={styles.fieldLabel}>Last Name</Text>
                <TextInput style={styles.fieldInput} value={profile.last_name} onChangeText={v => setProfile(p => ({ ...p, last_name: v }))} placeholderTextColor={colors.textSecondary} placeholder="Last name" />
              </View>
            </View>
            <Text style={styles.fieldLabel}>Email</Text>
            <TextInput style={styles.fieldInput} value={profile.email} editable={false} placeholderTextColor={colors.textSecondary} />
            <Text style={styles.fieldLabel}>Phone</Text>
            <TextInput style={styles.fieldInput} value={profile.phone} onChangeText={v => setProfile(p => ({ ...p, phone: v }))} placeholderTextColor={colors.textSecondary} placeholder="Phone number" keyboardType="phone-pad" />
            <Text style={styles.fieldLabel}>Date of Birth</Text>
            <TextInput style={styles.fieldInput} value={profile.date_of_birth} onChangeText={v => setProfile(p => ({ ...p, date_of_birth: v }))} placeholderTextColor={colors.textSecondary} placeholder="YYYY-MM-DD" />
          </View>
        );
      case 'medical_history':
        return (
          <View style={styles.section}>
            <Text style={styles.sectionDesc}>List any past surgeries, chronic conditions, or significant medical events.</Text>
            <TextInput style={styles.textArea} value={profile.medical_history} onChangeText={v => setProfile(p => ({ ...p, medical_history: v }))} placeholderTextColor={colors.textSecondary} placeholder="e.g., Asthma, Type 2 Diabetes, Appendectomy in 2020..." multiline numberOfLines={6} textAlignVertical="top" />
          </View>
        );
      case 'allergies':
        return (
          <View style={styles.section}>
            <Text style={styles.sectionDesc}>List any allergies to medications, foods, or environmental factors.</Text>
            <TextInput style={styles.textArea} value={profile.allergies} onChangeText={v => setProfile(p => ({ ...p, allergies: v }))} placeholderTextColor={colors.textSecondary} placeholder="e.g., Penicillin, Peanuts, Pollen..." multiline numberOfLines={4} textAlignVertical="top" />
            <Text style={styles.fieldLabel}>Blood Type</Text>
            <TextInput style={styles.fieldInput} value={profile.blood_type} onChangeText={v => setProfile(p => ({ ...p, blood_type: v }))} placeholderTextColor={colors.textSecondary} placeholder="A+, B-, O+, etc." />
          </View>
        );
      case 'medications':
        return (
          <View style={styles.section}>
            <Text style={styles.sectionDesc}>List current medications, including dosage and frequency.</Text>
            <TextInput style={styles.textArea} value={profile.medications} onChangeText={v => setProfile(p => ({ ...p, medications: v }))} placeholderTextColor={colors.textSecondary} placeholder="e.g., Metformin 500mg twice daily, Lisinopril 10mg daily..." multiline numberOfLines={6} textAlignVertical="top" />
          </View>
        );
      case 'vitals':
        return (
          <View style={styles.section}>
            <View style={styles.fieldRow}>
              <View style={styles.halfField}>
                <Text style={styles.fieldLabel}>Height (cm)</Text>
                <TextInput style={styles.fieldInput} value={profile.height_cm} onChangeText={v => setProfile(p => ({ ...p, height_cm: v }))} placeholderTextColor={colors.textSecondary} placeholder="170" keyboardType="numeric" />
              </View>
              <View style={styles.halfField}>
                <Text style={styles.fieldLabel}>Weight (kg)</Text>
                <TextInput style={styles.fieldInput} value={profile.weight_kg} onChangeText={v => setProfile(p => ({ ...p, weight_kg: v }))} placeholderTextColor={colors.textSecondary} placeholder="70" keyboardType="numeric" />
              </View>
            </View>
            <View style={styles.fieldRow}>
              <View style={styles.halfField}>
                <Text style={styles.fieldLabel}>Blood Pressure (SYS)</Text>
                <TextInput style={styles.fieldInput} value={profile.blood_pressure_sys} onChangeText={v => setProfile(p => ({ ...p, blood_pressure_sys: v }))} placeholderTextColor={colors.textSecondary} placeholder="120" keyboardType="numeric" />
              </View>
              <View style={styles.halfField}>
                <Text style={styles.fieldLabel}>Blood Pressure (DIA)</Text>
                <TextInput style={styles.fieldInput} value={profile.blood_pressure_dia} onChangeText={v => setProfile(p => ({ ...p, blood_pressure_dia: v }))} placeholderTextColor={colors.textSecondary} placeholder="80" keyboardType="numeric" />
              </View>
            </View>
            <Text style={styles.fieldLabel}>Heart Rate (bpm)</Text>
            <TextInput style={styles.fieldInput} value={profile.heart_rate} onChangeText={v => setProfile(p => ({ ...p, heart_rate: v }))} placeholderTextColor={colors.textSecondary} placeholder="72" keyboardType="numeric" />
          </View>
        );
      default:
        return null;
    }
  }

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  const progressWidth = progressAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>My Health</Text>
      </View>

      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressHeader}>
          <Text style={styles.progressLabel}>Profile Complete</Text>
          <Text style={styles.progressPercent}>{Math.round(progress)}%</Text>
        </View>
        <View style={styles.progressBarBg}>
          <Animated.View style={[styles.progressBarFill, { width: progressWidth }]} />
        </View>
      </View>

      {/* Section Tabs */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabsScroll} contentContainerStyle={styles.tabsContent}>
        {SECTIONS.map((section, index) => (
          <TouchableOpacity
            key={section.key}
            style={[styles.tab, activeSection === index && styles.tabActive]}
            onPress={() => setActiveSection(index)}
          >
            <Text style={styles.tabIcon}>{section.icon}</Text>
            <Text style={[styles.tabLabel, activeSection === index && styles.tabLabelActive]}>
              {section.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Content */}
      <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
        {renderSectionContent()}

        <TouchableOpacity
          style={[styles.saveBtn, saving && styles.saveBtnDisabled]}
          onPress={handleSave}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator color={colors.background} />
          ) : (
            <Text style={styles.saveBtnText}>Save Changes</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </View>
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
  header: {
    padding: 20,
    paddingBottom: 10,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.white,
  },
  progressContainer: {
    marginHorizontal: 20,
    marginBottom: 16,
    backgroundColor: colors.card,
    borderRadius: borderRadius.md,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  progressLabel: {
    fontSize: 13,
    color: colors.textSecondary,
  },
  progressPercent: {
    fontSize: 13,
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
  tabsScroll: {
    maxHeight: 80,
  },
  tabsContent: {
    paddingHorizontal: 16,
    gap: 8,
    paddingBottom: 8,
  },
  tab: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: colors.card,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.cardBorder,
    gap: 6,
  },
  tabActive: {
    borderColor: colors.accent,
    backgroundColor: colors.accent + '15',
  },
  tabIcon: {
    fontSize: 16,
  },
  tabLabel: {
    fontSize: 12,
    fontWeight: '500',
    color: colors.textSecondary,
  },
  tabLabelActive: {
    color: colors.accent,
  },
  content: {
    flex: 1,
  },
  contentInner: {
    padding: 20,
    paddingBottom: 40,
  },
  section: {
    backgroundColor: colors.card,
    borderRadius: borderRadius.lg,
    padding: 20,
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  sectionDesc: {
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: 16,
    lineHeight: 18,
  },
  fieldRow: {
    flexDirection: 'row',
    gap: 12,
  },
  halfField: {
    flex: 1,
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: '500',
    color: colors.text,
    marginBottom: 6,
    marginTop: 12,
  },
  fieldInput: {
    backgroundColor: colors.inputBg,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    borderRadius: borderRadius.sm,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: colors.white,
  },
  textArea: {
    backgroundColor: colors.inputBg,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    borderRadius: borderRadius.sm,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: colors.white,
    minHeight: 120,
    textAlignVertical: 'top',
  },
  saveBtn: {
    backgroundColor: colors.accent,
    borderRadius: borderRadius.md,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 20,
  },
  saveBtnDisabled: {
    opacity: 0.6,
  },
  saveBtnText: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.background,
  },
});
