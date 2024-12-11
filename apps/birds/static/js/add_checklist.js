const app = Vue.createApp({
    data() {
        return {
            searchQuery: '',
            speciesList: [],
            filteredSpecies: [],
            latitude: '',
            longitude: '',
            observationDate: '',
            timeObservationsStarted: '',
            durationMinutes: '',
            errors: {}, 
            speciesName: '', 
        };
    },
    computed: {
        hasErrors() {
            return (
                !this.latitude ||
                !this.longitude ||
                !this.observationDate ||
                !this.timeObservationsStarted ||
                !this.durationMinutes ||
                !this.speciesName.trim() ||
                !this.filteredSpecies.some(s => s.count > 0)
            );
        },
    },
    methods: {
        async fetchSpecies() {
            try {
                const response = await axios.get('/birds/search_species', {
                    params: { q: this.searchQuery },
                });
                this.speciesList = response.data.species.map(s => ({
                    ...s,
                    count: 0,
                }));
                this.filteredSpecies = this.speciesList;
            } catch (error) {
                console.error('Error fetching species data:', error);
            }
        },
        incrementCount(species) {
            if (!species.count) species.count = 0;
            species.count++;
        },
        resetForm() {
            this.latitude = '';
            this.longitude = '';
            this.observationDate = '';
            this.timeObservationsStarted = '';
            this.durationMinutes = '';
            this.speciesName = '';
            this.filteredSpecies = [];
            this.errors = {};
        },
        validateAndSubmit() {
            if (!this.hasErrors) {
                this.submitChecklist();
            } 
        },
        async submitChecklist() {
            const checklist = {
                speciesName: this.speciesName,
                latitude: this.latitude,
                longitude: this.longitude,
                observationDate: this.observationDate,
                timeObservationsStarted: this.timeObservationsStarted,
                durationMinutes: this.durationMinutes,
                species: this.filteredSpecies.filter(s => s.count > 0),
            };

            try {
                await axios.post('/birds/submit_checklist', checklist);
                this.resetForm();
                window.location.href = '/birds/my_checklists';
            } catch (error) {
                console.error('Error submitting checklist:', error);
            }
        },
    },
    mounted() {
        const themeToggleButton = document.getElementById('theme-toggle');
        
        // Theme Toggle Functionality
        themeToggleButton.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            themeToggleButton.textContent = document.body.classList.contains('dark-mode') ? '🌞' : '🌙';
        });

        // Get latitude and longitude from URL
        const params = new URLSearchParams(window.location.search);
        this.latitude = params.get('lat') || '';
        this.longitude = params.get('lng') || '';
    },
});

app.mount('#app');
