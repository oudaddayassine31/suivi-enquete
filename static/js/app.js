// ============================================================================
// STATE
// ============================================================================
const state = {
    selectedProvince: null,
    selectedZone: null,
    zoneConfigured: false,
    limiteFile: null,
    enqueteFile: null
};

// ============================================================================
// INITIALIZATION
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    attachEventListeners();
    document.getElementById('dateDebutInput').valueAsDate = new Date();
});

async function initApp() {
    await loadProvinces();
}

// ============================================================================
// DATA LOADING
// ============================================================================
async function loadProvinces() {
    try {
        const response = await fetch('/api/provinces');
        const provinces = await response.json();
        
        const select = document.getElementById('provinceSelect');
        provinces.forEach(province => {
            const option = document.createElement('option');
            option.value = province;
            option.textContent = province;
            select.appendChild(option);
        });
    } catch (error) {
        showToast('Erreur chargement provinces', 'error');
        console.error(error);
    }
}

async function loadZones(province) {
    try {
        const response = await fetch(`/api/zones/${province}`);
        const zones = await response.json();
        
        const select = document.getElementById('zoneSelect');
        select.innerHTML = '<option value="">-- Sélectionner Zone --</option>';
        
        zones.forEach(zone => {
            const option = document.createElement('option');
            option.value = zone.code;
            option.textContent = `${zone.code} - ${zone.nom}`;
            select.appendChild(option);
        });
        
        select.disabled = false;
    } catch (error) {
        showToast('Erreur chargement zones', 'error');
        console.error(error);
    }
}

async function loadZoneInfo(province, codeZone) {
    try {
        showLoading(true);
        
        const response = await fetch('/api/zone/info', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({province, code_zone: codeZone})
        });
        
        const info = await response.json();
        
        if (info.configured) {
            // Zone configurée
            state.zoneConfigured = true;
            
            // Masquer section limite
            document.getElementById('limiteSection').style.display = 'none';
            
            // Afficher sections
            document.getElementById('statsSection').style.display = 'block';
            document.getElementById('enqueteSection').style.display = 'block';
            document.getElementById('infoSection').style.display = 'block';
            
            // Gérer zone clôturée
            if (info.cloturee) {
                document.getElementById('clotureeeBadge').style.display = 'inline-block';
                document.getElementById('uploadEnqueteForm').style.display = 'none';
                document.getElementById('clotureeMessage').style.display = 'block';
                document.getElementById('limiteSection').style.display = 'none';
            } else {
                document.getElementById('clotureeeBadge').style.display = 'none';
                document.getElementById('uploadEnqueteForm').style.display = 'block';
                document.getElementById('clotureeMessage').style.display = 'none';
            }
            
            // Remplir info
            document.getElementById('infoProvince').textContent = province;
            document.getElementById('infoZone').textContent = info.nom_zone;
            document.getElementById('infoEnqueteur').textContent = info.enqueteur || '-';
            document.getElementById('infoDateDebut').textContent = info.date_debut_enquete || '-';
            
            // Remplir stats
            document.getElementById('statSurfaceZone').textContent = `${info.surface_totale_ha || 0} ha`;
            document.getElementById('statSurfaceEnquetee').textContent = `${info.surface_enquetee_ha || 0} ha`;
            document.getElementById('statSurfaceRestante').textContent = `${info.surface_restante_ha || 0} ha`;
            document.getElementById('statParcelles').textContent = info.nb_parcelles || 0;
            document.getElementById('statPourcentage').textContent = `${info.pourcentage_avancement || 0}%`;
            document.getElementById('statJour').textContent = `#${info.numero_jour || 0}`;
            
            // Avancement journalier
            const parcellesAjoutees = info.parcelles_ajoutees_aujourd_hui || 0;
            const surfaceAjoutee = info.surface_ajoutee_aujourd_hui || 0;
            document.getElementById('statParcellesAjoutees').textContent = parcellesAjoutees >= 0 ? `+${parcellesAjoutees}` : parcellesAjoutees;
            document.getElementById('statSurfaceAjoutee').textContent = surfaceAjoutee >= 0 ? `+${surfaceAjoutee} ha` : `${surfaceAjoutee} ha`;
            
            // Progress bar
            const progress = info.pourcentage_avancement || 0;
            document.getElementById('progressBar').style.width = `${progress}%`;
            
            // Pré-remplir numero jour
            document.getElementById('numeroJourInput').value = (info.numero_jour || 0) + 1;
            
            // Afficher historique
            if (info.historique && info.historique.length > 0) {
                displayHistorique(info.historique);
            }
            
            // Activer export
            document.getElementById('exportBtn').disabled = info.nb_parcelles === 0;
            
            showToast('Zone chargée avec succès', 'success');
        } else {
            // Zone non configurée
            state.zoneConfigured = false;
            
            // Afficher section limite
            document.getElementById('limiteSection').style.display = 'block';
            
            // Masquer autres sections
            document.getElementById('statsSection').style.display = 'none';
            document.getElementById('enqueteSection').style.display = 'none';
            document.getElementById('infoSection').style.display = 'none';
            document.getElementById('exportBtn').disabled = true;
            
            showToast('Zone non configurée. Veuillez uploader la limite.', 'warning');
        }
    } catch (error) {
        showToast('Erreur chargement zone', 'error');
        console.error(error);
    } finally {
        showLoading(false);
    }
}

function displayHistorique(historique) {
    const tbody = document.getElementById('historiqueTableBody');
    tbody.innerHTML = '';
    
    historique.forEach(h => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${h.date_maj}</td>
            <td>${h.numero_jour}</td>
            <td>${h.nb_parcelles}</td>
            <td>${h.surface_enquetee_ha}</td>
            <td class="${h.parcelles_ajoutees >= 0 ? 'positive' : 'negative'}">${h.parcelles_ajoutees >= 0 ? '+' : ''}${h.parcelles_ajoutees}</td>
            <td class="${h.surface_ajoutee_ha >= 0 ? 'positive' : 'negative'}">${h.surface_ajoutee_ha >= 0 ? '+' : ''}${h.surface_ajoutee_ha}</td>
        `;
        tbody.appendChild(row);
    });
    
    document.getElementById('historiqueSection').style.display = 'block';
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================
function attachEventListeners() {
    // Province
    document.getElementById('provinceSelect').addEventListener('change', (e) => {
        const province = e.target.value;
        if (province) {
            state.selectedProvince = province;
            loadZones(province);
            resetZone();
        }
    });
    
    // Zone
    document.getElementById('zoneSelect').addEventListener('change', (e) => {
        const codeZone = e.target.value;
        if (codeZone) {
            state.selectedZone = codeZone;
            loadZoneInfo(state.selectedProvince, codeZone);
        }
    });
    
    // Limite file
    document.getElementById('limiteFile').addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            state.limiteFile = file;
            document.getElementById('limiteFileName').textContent = file.name;
            updateLimiteButton();
        }
    });
    
    // Enqueteur et date debut
    document.getElementById('enqueteurInput').addEventListener('input', updateLimiteButton);
    document.getElementById('dateDebutInput').addEventListener('change', updateLimiteButton);
    
    // Upload limite
    document.getElementById('uploadLimiteBtn').addEventListener('click', uploadLimite);
    
    // Enquete file
    document.getElementById('enqueteFile').addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            state.enqueteFile = file;
            document.getElementById('enqueteFileName').textContent = file.name;
            updateEnqueteButton();
        }
    });
    
    // Numero jour
    document.getElementById('numeroJourInput').addEventListener('input', updateEnqueteButton);
    
    // Upload enquete
    document.getElementById('uploadEnqueteBtn').addEventListener('click', uploadEnquete);
    
    // Export
    document.getElementById('exportBtn').addEventListener('click', exportPH1);
}

function updateLimiteButton() {
    const enqueteur = document.getElementById('enqueteurInput').value.trim();
    const dateDebut = document.getElementById('dateDebutInput').value;
    const hasFile = state.limiteFile !== null;
    document.getElementById('uploadLimiteBtn').disabled = !(enqueteur && dateDebut && hasFile);
}

function updateEnqueteButton() {
    const numeroJour = document.getElementById('numeroJourInput').value;
    const hasFile = state.enqueteFile !== null;
    document.getElementById('uploadEnqueteBtn').disabled = !(numeroJour && hasFile);
}

function resetZone() {
    state.selectedZone = null;
    state.zoneConfigured = false;
    document.getElementById('limiteSection').style.display = 'none';
    document.getElementById('statsSection').style.display = 'none';
    document.getElementById('enqueteSection').style.display = 'none';
    document.getElementById('infoSection').style.display = 'none';
    document.getElementById('exportBtn').disabled = true;
}

// ============================================================================
// UPLOADS
// ============================================================================
async function uploadLimite() {
    if (!state.selectedProvince || !state.selectedZone || !state.limiteFile) {
        showToast('Veuillez remplir tous les champs', 'error');
        return;
    }
    
    const enqueteur = document.getElementById('enqueteurInput').value.trim();
    const dateDebut = document.getElementById('dateDebutInput').value;
    
    if (!enqueteur || !dateDebut) {
        showToast('Veuillez entrer l\'enquêteur et la date de début', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const formData = new FormData();
        formData.append('file', state.limiteFile);
        formData.append('province', state.selectedProvince);
        formData.append('code_zone', state.selectedZone);
        formData.append('enqueteur', enqueteur);
        formData.append('date_debut_enquete', dateDebut);
        
        const response = await fetch('/api/upload/limite', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`✅ ${result.message}`, 'success');
            
            // Reset form
            document.getElementById('limiteFile').value = '';
            document.getElementById('limiteFileName').textContent = '';
            state.limiteFile = null;
            
            // Reload zone
            await loadZoneInfo(state.selectedProvince, state.selectedZone);
        } else {
            showToast(`❌ Erreur: ${result.error}`, 'error');
        }
    } catch (error) {
        showToast('❌ Erreur lors de l\'upload', 'error');
        console.error(error);
    } finally {
        showLoading(false);
    }
}

async function uploadEnquete() {
    if (!state.selectedProvince || !state.selectedZone || !state.enqueteFile) {
        showToast('Veuillez remplir tous les champs', 'error');
        return;
    }
    
    const numeroJour = document.getElementById('numeroJourInput').value;
    
    if (!numeroJour) {
        showToast('Veuillez remplir le numéro de jour', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const formData = new FormData();
        formData.append('file', state.enqueteFile);
        formData.append('province', state.selectedProvince);
        formData.append('code_zone', state.selectedZone);
        formData.append('numero_jour', numeroJour);
        
        const response = await fetch('/api/upload/enquete', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`✅ ${result.message}`, 'success');
            
            // Update stats immediately
            document.getElementById('statParcelles').textContent = result.nb_parcelles;
            document.getElementById('statSurfaceEnquetee').textContent = `${result.surface_enquetee_ha} ha`;
            document.getElementById('statSurfaceRestante').textContent = `${result.surface_restante_ha} ha`;
            document.getElementById('statPourcentage').textContent = `${result.pourcentage_avancement}%`;
            document.getElementById('statJour').textContent = `#${numeroJour}`;
            document.getElementById('progressBar').style.width = `${result.pourcentage_avancement}%`;
            
            // Update avancement journalier
            document.getElementById('statParcellesAjoutees').textContent = `+${result.parcelles_ajoutees}`;
            document.getElementById('statSurfaceAjoutee').textContent = `+${result.surface_ajoutee_ha} ha`;
            
            // Reset form
            document.getElementById('enqueteFile').value = '';
            document.getElementById('enqueteFileName').textContent = '';
            state.enqueteFile = null;
            
            // Increment numero jour
            document.getElementById('numeroJourInput').value = parseInt(numeroJour) + 1;
            
            // Enable export
            document.getElementById('exportBtn').disabled = false;
            
            // Reload zone
            await loadZoneInfo(state.selectedProvince, state.selectedZone);
        } else {
            showToast(`❌ Erreur: ${result.error}`, 'error');
        }
    } catch (error) {
        showToast('❌ Erreur lors de l\'upload', 'error');
        console.error(error);
    } finally {
        showLoading(false);
    }
}

// ============================================================================
// EXPORT
// ============================================================================
function exportPH1() {
    if (!state.selectedProvince || !state.selectedZone) {
        showToast('Veuillez sélectionner une zone', 'error');
        return;
    }
    
    window.location.href = `/api/export/ph1/${state.selectedProvince}/${state.selectedZone}`;
    showToast('Téléchargement Excel PH1 en cours...', 'success');
}

// ============================================================================
// UI UTILITIES
// ============================================================================
function showLoading(show) {
    document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => container.removeChild(toast), 300);
    }, 4000);
}