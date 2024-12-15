document.addEventListener('DOMContentLoaded', () => {
    const { createApp, ref, computed, onMounted } = Vue;

    const app = createApp({
        setup() {
            // Form data
            const latitude = ref('');
            const longitude = ref('');
            const observationDate = ref('');
            const timeObservationsStarted = ref('');
            const durationMinutes = ref(null);
            const errors = ref({});
            const selectedSpecies = ref([]);
            const searchQuery = ref('');
            const speciesList = ref([]);
            const currentLocation = ref(null);

            // Theme toggle logic
            const toggleTheme = () => {
                document.body.classList.toggle('dark-mode');
                localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
            };

            // Initialize theme and geolocation
            onMounted(() => {
                const savedTheme = localStorage.getItem('theme');
                if (savedTheme === 'dark') {
                    document.body.classList.add('dark-mode');
                }
                document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

                // Get user's current location
                if ("geolocation" in navigator) {
                    navigator.geolocation.getCurrentPosition((position) => {
                        const coords = position.coords;
                        currentLocation.value = {
                            latitude: coords.latitude.toFixed(6),
                            longitude: coords.longitude.toFixed(6)
                        };
                        latitude.value = coords.latitude.toFixed(6);
                        longitude.value = coords.longitude.toFixed(6);
                    }, (error) => {
                        console.error("Error getting location:", error);
                        alert('Could not retrieve location. Please enter manually or try again.');
                    });
                }
            });

            // Fetch species list
            const fetchSpecies = async () => {
                try {
                    const response = await axios.get('/get_species');
                    speciesList.value = response.data.species || [];
                } catch (error) {
                    console.error('Error fetching species:', error);
                    alert('Failed to load species list. Please refresh the page.');
                }
            };

            // Filtered species based on search query
            const filteredSpecies = computed(() => {
                return speciesList.value.filter(species => 
                    species.COMMON_NAME.toLowerCase().includes(searchQuery.value.toLowerCase())
                );
            });

            // Increment species count in the checklist
            const incrementCount = (species) => {
                const existingSpecies = selectedSpecies.value.find(s => s.COMMON_NAME === species.COMMON_NAME);
                if (existingSpecies) {
                    existingSpecies.count = (existingSpecies.count || 0) + 1;
                } else {
                    selectedSpecies.value.push({
                        COMMON_NAME: species.COMMON_NAME,
                        count: 1
                    });
                }
            };

            // Remove species from selected list
            const removeSpecies = (speciesName) => {
                selectedSpecies.value = selectedSpecies.value.filter(
                    species => species.COMMON_NAME !== speciesName
                );
            };

            // Validate form
            const validateForm = () => {
                errors.value = {};

                if (!observationDate.value) {
                    errors.value.observationDate = 'Observation date is required';
                }

                if (!timeObservationsStarted.value) {
                    errors.value.timeObservationsStarted = 'Start time is required';
                }

                if (!durationMinutes.value || durationMinutes.value <= 0) {
                    errors.value.durationMinutes = 'Duration must be a positive number';
                }

                if (selectedSpecies.value.length === 0) {
                    errors.value.species = 'At least one species must be added to the checklist';
                }

                return Object.keys(errors.value).length === 0;
            };

            // Submit checklist
            const validateAndSubmit = async () => {
                if (!validateForm()) return;

                try {
                    const checklistData = {
                        latitude: latitude.value,
                        longitude: longitude.value,
                        observationDate: observationDate.value,
                        timeObservationsStarted: timeObservationsStarted.value,
                        durationMinutes: durationMinutes.value,
                        species: selectedSpecies.value
                    };

                    const response = await axios.post('/submit_checklist', checklistData);

                    if (response.data.status === 'success') {
                        alert('Checklist submitted successfully!');
                        resetForm();
                    } else {
                        alert('Error submitting checklist: ' + (response.data.message || 'Unknown error'));
                    }
                } catch (error) {
                    console.error('Submission error:', error);
                    alert('Error submitting checklist. Please try again.');
                }
            };

            // Reset form
            const resetForm = () => {
                observationDate.value = '';
                timeObservationsStarted.value = '';
                durationMinutes.value = null;
                selectedSpecies.value = [];
                errors.value = {};
            };

            // Fetch species on component mount
            onMounted(fetchSpecies);

            return {
                latitude,
                longitude,
                observationDate,
                timeObservationsStarted,
                durationMinutes,
                errors,
                selectedSpecies,
                searchQuery,
                filteredSpecies,
                incrementCount,
                removeSpecies,
                validateAndSubmit,
                resetForm,
                hasErrors: computed(() => Object.keys(errors.value).length > 0)
            };
        }
    });

    app.mount('#app');
});