import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList,
  Image, Alert, ActivityIndicator,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as FileSystem from 'expo-file-system';
import { colors, borderRadius } from '../theme';
import { useAuth } from '../context/AuthContext';
import apiClient from '../api/client';

export default function MedicalRecordsScreen({ navigation }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadRecords();
    requestPermissions();
  }, []);

  async function requestPermissions() {
    const { status: cameraStatus } = await ImagePicker.requestCameraPermissionsAsync();
    const { status: galleryStatus } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (cameraStatus !== 'granted' || galleryStatus !== 'granted') {
      Alert.alert('Permissions needed', 'Camera and gallery access needed for medical records');
    }
  }

  async function loadRecords() {
    setLoading(true);
    try {
      const profile = await apiClient.getProfile();
      if (profile && profile.medical_records) {
        setRecords(profile.medical_records);
      }
    } catch (e) {
      // Use empty state
    } finally {
      setLoading(false);
    }
  }

  async function pickFromCamera() {
    const result = await ImagePicker.launchCameraAsync({
      quality: 0.8,
      base64: false,
    });
    if (!result.canceled && result.assets?.[0]) {
      await uploadFile(result.assets[0].uri);
    }
  }

  async function pickFromGallery() {
    const result = await ImagePicker.launchImageLibraryAsync({
      quality: 0.8,
      base64: false,
    });
    if (!result.canceled && result.assets?.[0]) {
      await uploadFile(result.assets[0].uri);
    }
  }

  async function uploadFile(uri) {
    setUploading(true);
    try {
      const formData = new FormData();
      const filename = uri.split('/').pop();
      const ext = filename.split('.').pop();
      formData.append('file', {
        uri,
        name: filename,
        type: `image/${ext === 'png' ? 'png' : 'jpeg'}`,
      });

      await apiClient.request('/api/patient/upload-record', {
        method: 'POST',
        body: formData,
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      Alert.alert('Success', 'Medical record uploaded');
      loadRecords();
    } catch (e) {
      Alert.alert('Upload Failed', e.message);
    } finally {
      setUploading(false);
    }
  }

  async function deleteRecord(recordId) {
    Alert.alert('Delete Record', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await apiClient.request(`/api/patient/records/${recordId}`, {
              method: 'DELETE',
            });
            setRecords(prev => prev.filter(r => r.id !== recordId));
          } catch (e) {
            Alert.alert('Error', e.message);
          }
        },
      },
    ]);
  }

  function renderRecord({ item }) {
    return (
      <View style={styles.recordCard}>
        <Image source={{ uri: item.url || item.image_url }} style={styles.recordImage} />
        <View style={styles.recordInfo}>
          <Text style={styles.recordName}>{item.name || 'Medical Record'}</Text>
          <Text style={styles.recordDate}>{item.created_at || item.uploaded_at || ''}</Text>
        </View>
        <TouchableOpacity
          style={styles.deleteBtn}
          onPress={() => deleteRecord(item.id)}
        >
          <Text style={styles.deleteText}>✕</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Medical Records</Text>
        <Text style={styles.subtitle}>Upload and manage your medical documents</Text>
      </View>

      <View style={styles.uploadButtons}>
        <TouchableOpacity
          style={[styles.uploadBtn, styles.cameraBtn]}
          onPress={pickFromCamera}
          disabled={uploading}
        >
          <Text style={styles.uploadIcon}>📷</Text>
          <Text style={styles.uploadBtnText}>Camera</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.uploadBtn, styles.galleryBtn]}
          onPress={pickFromGallery}
          disabled={uploading}
        >
          <Text style={styles.uploadIcon}>🖼️</Text>
          <Text style={styles.uploadBtnText}>Gallery</Text>
        </TouchableOpacity>
      </View>

      {uploading && (
        <View style={styles.uploadingBanner}>
          <ActivityIndicator color={colors.accent} size="small" />
          <Text style={styles.uploadingText}>Uploading...</Text>
        </View>
      )}

      {loading ? (
        <View style={styles.centerContent}>
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      ) : records.length === 0 ? (
        <View style={styles.centerContent}>
          <Text style={styles.emptyIcon}>📁</Text>
          <Text style={styles.emptyText}>No medical records yet</Text>
          <Text style={styles.emptySubtext}>Upload from camera or gallery above</Text>
        </View>
      ) : (
        <FlatList
          data={records}
          renderItem={renderRecord}
          keyExtractor={(item, index) => String(item.id || index)}
          contentContainerStyle={styles.list}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
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
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 4,
  },
  uploadButtons: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    gap: 12,
    marginBottom: 16,
  },
  uploadBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    borderRadius: borderRadius.md,
    gap: 8,
  },
  cameraBtn: {
    backgroundColor: '#4a9eff30',
    borderWidth: 1,
    borderColor: '#4a9eff',
  },
  galleryBtn: {
    backgroundColor: '#51cf6630',
    borderWidth: 1,
    borderColor: '#51cf66',
  },
  uploadIcon: {
    fontSize: 20,
  },
  uploadBtnText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
  },
  uploadingBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 8,
    backgroundColor: colors.card,
    marginHorizontal: 20,
    borderRadius: borderRadius.sm,
    marginBottom: 8,
  },
  uploadingText: {
    color: colors.accent,
    fontSize: 13,
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 60,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 16,
    color: colors.text,
    fontWeight: '600',
  },
  emptySubtext: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 4,
  },
  list: {
    padding: 20,
    paddingTop: 0,
  },
  recordCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.card,
    borderRadius: borderRadius.md,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  recordImage: {
    width: 56,
    height: 56,
    borderRadius: borderRadius.sm,
    backgroundColor: colors.inputBg,
  },
  recordInfo: {
    flex: 1,
    marginLeft: 12,
  },
  recordName: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
  },
  recordDate: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  deleteBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: colors.error + '20',
    justifyContent: 'center',
    alignItems: 'center',
  },
  deleteText: {
    color: colors.error,
    fontSize: 14,
    fontWeight: '700',
  },
});
