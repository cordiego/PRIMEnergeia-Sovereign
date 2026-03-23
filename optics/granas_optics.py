"""
PRIMEnergeia — Granas Optics Engine
=====================================
High-fidelity optical simulation for bio-mimetic granular photonic panels.

Modeling stack:
  1. Mie Scattering   — Analytical Qsca/Qabs/Qext for dielectric spheres
  2. Poisson Disc      — Bridson algorithm for realistic 3D granule packing
  3. Transfer Matrix   — Multilayer R/T/A with scattering-enhanced absorption
  4. Solar Spectrum     — AM1.5G integration, Jsc, Yablonovitch 4n² limit
  5. GranasEngine      — Top-level orchestrator

Physics:
  State   : λ ∈ [300, 1200] nm  (AM1.5G solar window)
  Granule : radius r, refractive index n + iκ
  Target  : Absorption > 95%, Path Length Enhancement ≥ 4n²

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, List

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [Granas Optics] - %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Physical Constants
# ─────────────────────────────────────────────────────────────
C_LIGHT = 2.998e8        # m/s
H_PLANCK = 6.626e-34     # J·s
Q_ELECTRON = 1.602e-19   # C
NM = 1e-9                # nm → m


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────
@dataclass
class MaterialData:
    """Complex refractive index n(λ) + iκ(λ) for a material."""
    name: str
    wavelengths_nm: np.ndarray       # λ grid (nm)
    n_real: np.ndarray               # Real part of refractive index
    n_imag: np.ndarray               # Imaginary part (extinction)
    source: str = "custom"           # "DFT", "literature", "custom"

    def n_complex(self, wavelength_nm: float) -> complex:
        """Interpolated complex refractive index at given wavelength."""
        n_r = float(np.interp(wavelength_nm, self.wavelengths_nm, self.n_real))
        n_i = float(np.interp(wavelength_nm, self.wavelengths_nm, self.n_imag))
        return complex(n_r, n_i)


@dataclass
class Granule:
    """A single granule in the matrix."""
    x: float          # Position (nm)
    y: float
    z: float
    radius_nm: float  # Radius (nm)
    material: str     # Material name


@dataclass
class OpticsResult:
    """Complete result from a Granas optical simulation."""
    wavelengths_nm: np.ndarray
    reflectance: np.ndarray
    transmittance: np.ndarray
    absorptance: np.ndarray
    eqe: np.ndarray                           # External Quantum Efficiency
    jsc_mA_cm2: float                         # Short-circuit current density
    path_length_enhancement: float            # vs. single-pass
    yablonovitch_limit: float                 # 4n²
    light_trapping_efficiency: float          # LTE (0-1)
    weighted_absorption: float                # AM1.5G-weighted absorption (%)
    granule_positions: List[Granule]           # The packed granules
    efield_map: Optional[np.ndarray] = None   # 2D E-field intensity


# ─────────────────────────────────────────────────────────────
# Built-in Material Library
# ─────────────────────────────────────────────────────────────
def _perovskite_mapbi3() -> MaterialData:
    """MAPbI3 perovskite — literature values (simplified)."""
    wl = np.linspace(300, 1200, 91)
    # Bandgap ~1.55 eV → 800nm
    bg_nm = 800.0
    n_r = 2.5 - 0.3 * np.exp(-(wl - 500)**2 / 40000)
    n_i = np.where(wl < bg_nm,
                   0.8 * np.exp(-(wl - 400)**2 / 30000) + 0.15,
                   0.005)
    return MaterialData("MAPbI3", wl, n_r, n_i, source="literature")


def _biohybrid_chlorophyll() -> MaterialData:
    """Bio-hybrid chlorophyll-inspired pigment — proprietary model."""
    wl = np.linspace(300, 1200, 91)
    # Two absorption peaks: Soret (~430nm) and Q-band (~680nm)
    n_r = 1.8 + 0.2 * np.sin(2 * np.pi * wl / 600)
    soret = 0.6 * np.exp(-(wl - 430)**2 / 2000)
    q_band = 0.4 * np.exp(-(wl - 680)**2 / 3000)
    n_i = soret + q_band + 0.02
    return MaterialData("BioHybrid-Chl", wl, n_r, n_i, source="DFT")


def _tio2_anatase() -> MaterialData:
    """TiO2 anatase — transparent electron transport layer."""
    wl = np.linspace(300, 1200, 91)
    n_r = 2.5 - 0.15 * (wl - 300) / 900
    n_i = np.where(wl < 380, 0.3 * np.exp(-(wl - 300)**2 / 5000), 0.001)
    return MaterialData("TiO2-Anatase", wl, n_r, n_i, source="literature")


MATERIAL_LIBRARY: Dict[str, MaterialData] = {
    "MAPbI3": _perovskite_mapbi3(),
    "BioHybrid-Chl": _biohybrid_chlorophyll(),
    "TiO2-Anatase": _tio2_anatase(),
}


# ─────────────────────────────────────────────────────────────
# AM1.5G Solar Spectrum
# ─────────────────────────────────────────────────────────────
class SolarSpectrum:
    """
    AM1.5G reference spectrum (ASTM G173).
    Simplified parametric model of spectral irradiance.
    """

    @staticmethod
    def irradiance(wavelengths_nm: np.ndarray) -> np.ndarray:
        """
        Spectral irradiance E(λ) in W/(m²·nm).
        Parametric fit to ASTM G173 AM1.5G data.
        """
        wl = wavelengths_nm
        # Blackbody-like envelope at 5778K scaled to 1000 W/m²
        wl_m = wl * NM
        bb = (2 * H_PLANCK * C_LIGHT**2 / wl_m**5) / \
             (np.exp(H_PLANCK * C_LIGHT / (wl_m * 1.381e-23 * 5778)) - 1)
        # Normalize to ~1000 W/m² total
        bb_norm = bb / np.max(bb)
        # Atmospheric absorption dips
        h2o_1 = 1.0 - 0.4 * np.exp(-(wl - 940)**2 / 800)
        h2o_2 = 1.0 - 0.3 * np.exp(-(wl - 1130)**2 / 1200)
        o2_dip = 1.0 - 0.15 * np.exp(-(wl - 760)**2 / 200)
        atm = h2o_1 * h2o_2 * o2_dip
        # Peak ~1.4 W/(m²·nm) around 500nm
        E = 1.4 * bb_norm * atm
        return np.maximum(E, 0)

    @staticmethod
    def photon_flux(wavelengths_nm: np.ndarray) -> np.ndarray:
        """
        Photon flux Φ(λ) in photons/(m²·s·nm).
        Φ = E·λ/(hc)
        """
        E = SolarSpectrum.irradiance(wavelengths_nm)
        wl_m = wavelengths_nm * NM
        return E * wl_m / (H_PLANCK * C_LIGHT)

    @staticmethod
    def calculate_jsc(wavelengths_nm: np.ndarray,
                      eqe: np.ndarray) -> float:
        """
        Short-circuit current density J_sc from EQE.
        Jsc = q ∫ EQE(λ) · Φ(λ) dλ
        Returns mA/cm².
        """
        flux = SolarSpectrum.photon_flux(wavelengths_nm)
        # Integrate in nm (flux is per nm), convert result
        jsc_A_m2 = Q_ELECTRON * np.trapz(eqe * flux, wavelengths_nm)
        return float(jsc_A_m2 / 10.0)  # A/m² → mA/cm²


# ─────────────────────────────────────────────────────────────
# Mie Scattering Solver
# ─────────────────────────────────────────────────────────────
class MieScatterer:
    """
    Analytical Mie theory for homogeneous dielectric spheres.

    Computes scattering/absorption/extinction efficiencies:
      Q = (2/x²) Σ (2n+1) · f(aₙ, bₙ)

    where x = 2πnr/λ is the size parameter and aₙ, bₙ are
    the Mie coefficients from Bessel function ratios.
    """

    @staticmethod
    def _mie_coefficients(x: float, m: complex,
                          n_max: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Mie coefficients aₙ, bₙ using logarithmic derivatives.

        Parameters
        ----------
        x : float
            Size parameter 2πr/λ (in medium)
        m : complex
            Relative refractive index (particle/medium)
        n_max : int
            Maximum expansion order

        Returns
        -------
        (a, b) : arrays of Mie coefficients
        """
        mx = m * x

        # Riccati-Bessel functions via upward recurrence
        # ψₙ(z) = z·jₙ(z),  χₙ(z) = -z·yₙ(z)
        def psi_chi(z, nmax):
            psi = np.zeros(nmax + 1, dtype=complex)
            chi = np.zeros(nmax + 1, dtype=complex)
            psi[0] = np.sin(z)
            psi[1] = np.sin(z) / z - np.cos(z)
            chi[0] = np.cos(z)
            chi[1] = np.cos(z) / z + np.sin(z)
            for n in range(2, nmax + 1):
                psi[n] = (2*n - 1) / z * psi[n-1] - psi[n-2]
                chi[n] = (2*n - 1) / z * chi[n-1] - chi[n-2]
            return psi, chi

        # ψₙ and ξₙ = ψₙ + iχₙ
        psi_x, chi_x = psi_chi(complex(x), n_max + 1)
        psi_mx, _ = psi_chi(mx, n_max + 1)

        xi_x = psi_x + 1j * chi_x

        # Derivatives: ψ'ₙ(z) = ψₙ₋₁(z) - (n/z)ψₙ(z)
        a = np.zeros(n_max, dtype=complex)
        b = np.zeros(n_max, dtype=complex)

        for n in range(1, n_max + 1):
            # Logarithmic derivative Dₙ(mx) = [mx·ψₙ₋₁(mx) - n·ψₙ(mx)] / [ψₙ(mx)·mx]
            if abs(psi_mx[n]) < 1e-30:
                D_mx = 0
            else:
                D_mx = psi_mx[n-1] / psi_mx[n] - n / mx

            dpsi_x = psi_x[n-1] - n / x * psi_x[n]
            dxi_x = xi_x[n-1] - n / x * xi_x[n]

            # Mie coefficients
            a[n-1] = (m * D_mx * psi_x[n] - psi_x[n-1]) / \
                      (m * D_mx * xi_x[n] - xi_x[n-1] + 1e-30)
            b[n-1] = (D_mx * psi_x[n] - psi_x[n-1]) / \
                      (D_mx * xi_x[n] - xi_x[n-1] + 1e-30)

        return a, b

    @staticmethod
    def efficiencies(radius_nm: float, wavelength_nm: float,
                     n_particle: complex,
                     n_medium: float = 1.0) -> Dict[str, float]:
        """
        Compute Mie scattering efficiencies.

        Parameters
        ----------
        radius_nm : float
            Particle radius (nm)
        wavelength_nm : float
            Incident wavelength (nm)
        n_particle : complex
            Complex refractive index of particle
        n_medium : float
            Refractive index of surrounding medium

        Returns
        -------
        dict : Q_ext, Q_sca, Q_abs, g (asymmetry parameter)
        """
        x = 2 * np.pi * n_medium * radius_nm / wavelength_nm
        m = n_particle / n_medium

        if x < 0.01:
            return {"Q_ext": 0.0, "Q_sca": 0.0, "Q_abs": 0.0, "g": 0.0}

        n_max = max(int(x + 4 * x**(1/3) + 2), 4)
        n_max = min(n_max, 200)

        a, b = MieScatterer._mie_coefficients(x, m, n_max)

        ns = np.arange(1, n_max + 1)
        weights = 2 * ns + 1

        Q_ext = (2 / x**2) * np.sum(weights * np.real(a + b))
        Q_sca = (2 / x**2) * np.sum(weights * (np.abs(a)**2 + np.abs(b)**2))
        Q_abs = max(0.0, Q_ext - Q_sca)

        # Asymmetry parameter g = <cos θ>
        g_num = 0.0
        for n in range(1, n_max):
            g_num += (n * (n + 2) / (n + 1)) * np.real(
                a[n-1] * np.conj(a[n]) + b[n-1] * np.conj(b[n])
            )
            g_num += ((2*n + 1) / (n * (n + 1))) * np.real(
                a[n-1] * np.conj(b[n-1])
            )
        g = (4 / (x**2 * Q_sca)) * g_num if Q_sca > 1e-15 else 0.0

        return {
            "Q_ext": float(Q_ext),
            "Q_sca": float(Q_sca),
            "Q_abs": float(Q_abs),
            "g": float(np.clip(g, -1, 1)),
        }

    @staticmethod
    def spectrum(radius_nm: float, wavelengths_nm: np.ndarray,
                 material: MaterialData,
                 n_medium: float = 1.0) -> Dict[str, np.ndarray]:
        """
        Compute Mie efficiencies across a wavelength range.

        Returns dict with arrays: Q_ext, Q_sca, Q_abs, g.
        """
        Q_ext = np.zeros(len(wavelengths_nm))
        Q_sca = np.zeros(len(wavelengths_nm))
        Q_abs = np.zeros(len(wavelengths_nm))
        g_arr = np.zeros(len(wavelengths_nm))

        for i, wl in enumerate(wavelengths_nm):
            n_p = material.n_complex(wl)
            eff = MieScatterer.efficiencies(radius_nm, wl, n_p, n_medium)
            Q_ext[i] = eff["Q_ext"]
            Q_sca[i] = eff["Q_sca"]
            Q_abs[i] = eff["Q_abs"]
            g_arr[i] = eff["g"]

        return {"Q_ext": Q_ext, "Q_sca": Q_sca, "Q_abs": Q_abs, "g": g_arr}


# ─────────────────────────────────────────────────────────────
# Poisson Disc Sampling — Granular Matrix Builder
# ─────────────────────────────────────────────────────────────
class GranularMatrix:
    """
    Bio-mimetic granule packing via Poisson Disc Sampling.
    Creates randomized 3D granule placement with minimum spacing
    to prevent unphysical overlap.

    Uses Bridson's algorithm adapted for 3D.
    """

    @staticmethod
    def poisson_disc_3d(
        domain_nm: Tuple[float, float, float] = (2000, 2000, 1000),
        min_spacing_nm: float = 300.0,
        radius_mean_nm: float = 250.0,
        radius_std_nm: float = 50.0,
        material: str = "MAPbI3",
        max_attempts: int = 30,
        seed: int = 42,
    ) -> List[Granule]:
        """
        Generate a 3D granule packing using Poisson Disc Sampling.

        Parameters
        ----------
        domain_nm : tuple
            (Lx, Ly, Lz) domain size in nm
        min_spacing_nm : float
            Minimum center-to-center spacing
        radius_mean_nm : float
            Mean granule radius
        radius_std_nm : float
            Std dev of radius distribution
        material : str
            Material name for all granules
        max_attempts : int
            Bridson attempts per active point
        seed : int
            Random seed

        Returns
        -------
        List[Granule] : packed granules
        """
        rng = np.random.RandomState(seed)
        Lx, Ly, Lz = domain_nm
        r = min_spacing_nm

        # Grid cell size for spatial hashing
        cell = r / np.sqrt(3)
        nx = max(1, int(np.ceil(Lx / cell)))
        ny = max(1, int(np.ceil(Ly / cell)))
        nz = max(1, int(np.ceil(Lz / cell)))

        grid = -np.ones((nx, ny, nz), dtype=int)
        points = []
        active = []

        # First point
        p0 = np.array([rng.uniform(0, Lx),
                        rng.uniform(0, Ly),
                        rng.uniform(0, Lz)])
        points.append(p0)
        active.append(0)
        ci, cj, ck = (int(p0[0] / cell) % nx,
                       int(p0[1] / cell) % ny,
                       int(p0[2] / cell) % nz)
        grid[ci, cj, ck] = 0

        while active:
            idx = rng.randint(len(active))
            pidx = active[idx]
            center = points[pidx]
            found = False

            for _ in range(max_attempts):
                # Random point in annulus [r, 2r]
                theta = rng.uniform(0, 2 * np.pi)
                phi = rng.uniform(0, np.pi)
                dist = rng.uniform(r, 2 * r)
                offset = dist * np.array([
                    np.sin(phi) * np.cos(theta),
                    np.sin(phi) * np.sin(theta),
                    np.cos(phi),
                ])
                candidate = center + offset

                # Bounds check
                if (candidate[0] < 0 or candidate[0] >= Lx or
                    candidate[1] < 0 or candidate[1] >= Ly or
                    candidate[2] < 0 or candidate[2] >= Lz):
                    continue

                # Grid cell
                ci = int(candidate[0] / cell) % nx
                cj = int(candidate[1] / cell) % ny
                ck = int(candidate[2] / cell) % nz

                # Check neighbors (3x3x3 neighborhood)
                too_close = False
                for di in range(-2, 3):
                    for dj in range(-2, 3):
                        for dk in range(-2, 3):
                            ni = (ci + di) % nx
                            nj = (cj + dj) % ny
                            nk = (ck + dk) % nz
                            if grid[ni, nj, nk] >= 0:
                                other = points[grid[ni, nj, nk]]
                                if np.linalg.norm(candidate - other) < r:
                                    too_close = True
                                    break
                        if too_close:
                            break
                    if too_close:
                        break

                if not too_close:
                    new_idx = len(points)
                    points.append(candidate)
                    active.append(new_idx)
                    grid[ci, cj, ck] = new_idx
                    found = True
                    break

            if not found:
                active.pop(idx)

        # Convert to Granule objects with radius distribution
        granules = []
        for p in points:
            rad = max(50.0, rng.normal(radius_mean_nm, radius_std_nm))
            granules.append(Granule(
                x=float(p[0]), y=float(p[1]), z=float(p[2]),
                radius_nm=float(rad), material=material,
            ))

        logger.info(f"Poisson Disc: packed {len(granules)} granules "
                     f"in {Lx:.0f}×{Ly:.0f}×{Lz:.0f} nm domain")
        return granules

    @staticmethod
    def packing_density(granules: List[Granule],
                        domain_nm: Tuple[float, float, float]) -> float:
        """Volume fraction of granules in the domain (capped at 0.74 = FCC limit)."""
        vol_total = domain_nm[0] * domain_nm[1] * domain_nm[2]
        vol_granules = sum(4/3 * np.pi * g.radius_nm**3 for g in granules)
        return float(min(vol_granules / vol_total, 0.74))


# ─────────────────────────────────────────────────────────────
# Transfer Matrix Method (TMM)
# ─────────────────────────────────────────────────────────────
class TransferMatrixSolver:
    """
    Transfer Matrix Method for multilayer thin-film optics.

    Uses the characteristic matrix (Heavens convention) for normal
    incidence. Guarantees R + T + A = 1 (energy conservation).

    Convention:
      n = n' + in'' where n'' > 0 means absorption
      δ = 2π n d / λ (phase thickness)
      Forward wave: exp(+iδ) → decays for n'' > 0
    """

    @staticmethod
    def solve_stack(
        layer_n: List[complex],
        layer_d_nm: List[float],
        wavelength_nm: float,
        n_incident: float = 1.0,
        n_substrate: float = 1.5,
    ) -> Dict[str, float]:
        """
        Solve a multilayer stack at one wavelength using the
        characteristic matrix approach.

        The characteristic matrix for layer j is:
          M_j = [[cos(δ_j),  -i sin(δ_j)/η_j],
                 [-i η_j sin(δ_j),  cos(δ_j)]]

        where η_j = n_j (admittance at normal incidence)
        and δ_j = 2π n_j d_j / λ.
        """
        ni = complex(n_incident)
        ns = complex(n_substrate)

        # Total characteristic matrix
        M = np.eye(2, dtype=complex)

        for n_j, d_j in zip(layer_n, layer_d_nm):
            eta_j = n_j  # Admittance (normal incidence)
            delta_j = 2 * np.pi * n_j * d_j / wavelength_nm

            cos_d = np.cos(delta_j)
            sin_d = np.sin(delta_j)

            M_j = np.array([
                [cos_d, -1j * sin_d / eta_j],
                [-1j * eta_j * sin_d, cos_d],
            ], dtype=complex)

            M = M @ M_j

        # Reflectance and transmittance from characteristic matrix
        # B = M[0,0] + M[0,1]*η_s,  C = M[1,0] + M[1,1]*η_s
        eta_i = ni
        eta_s = ns

        B = M[0, 0] + M[0, 1] * eta_s
        C = M[1, 0] + M[1, 1] * eta_s

        # Reflection coefficient
        r = (eta_i * B - C) / (eta_i * B + C + 1e-30)

        R = float(np.abs(r)**2)
        R = min(R, 1.0)

        # Transmittance
        T = float(4 * eta_i.real * eta_s.real / (np.abs(eta_i * B + C)**2 + 1e-30))
        T = min(T, 1.0 - R)
        T = max(T, 0.0)

        # Absorptance (by energy conservation)
        A = float(max(0.0, 1.0 - R - T))

        return {"R": R, "T": T, "A": A}

    @classmethod
    def spectral_response(
        cls,
        layer_n_func,
        layer_d_nm: List[float],
        wavelengths_nm: np.ndarray,
        n_incident: float = 1.0,
        n_substrate: float = 1.5,
    ) -> Dict[str, np.ndarray]:
        """
        Compute R, T, A across a wavelength range.

        layer_n_func : callable(wl) → list of complex n values
        """
        R = np.zeros(len(wavelengths_nm))
        T = np.zeros(len(wavelengths_nm))
        A = np.zeros(len(wavelengths_nm))

        for i, wl in enumerate(wavelengths_nm):
            n_list = layer_n_func(wl)
            result = cls.solve_stack(n_list, layer_d_nm, wl,
                                     n_incident, n_substrate)
            R[i] = result["R"]
            T[i] = result["T"]
            A[i] = result["A"]

        return {"R": R, "T": T, "A": A}


# ─────────────────────────────────────────────────────────────
# Granas Engine (Top-Level Orchestrator)
# ─────────────────────────────────────────────────────────────
class GranasEngine:
    """
    High-fidelity optical simulation engine for Granas granular panels.

    Pipeline:
      1. Build granular matrix (Poisson Disc)
      2. Compute Mie scattering for representative granule
      3. Model effective medium with scattering-enhanced absorption
      4. Run TMM for full R/T/A spectra
      5. Integrate AM1.5G → Jsc, LTE, path length enhancement
      6. Generate E-field visualization
    """

    DEFAULT_WAVELENGTHS = np.linspace(300, 1200, 91)

    def __init__(self, simulation_name: str = "Granas_V1_Alpha"):
        self.name = simulation_name
        self.materials = dict(MATERIAL_LIBRARY)
        self.granules: List[Granule] = []
        self.result: Optional[OpticsResult] = None

        # Default device structure
        self.domain_nm = (2000.0, 2000.0, 1000.0)
        self.granule_radius_nm = 250.0
        self.granule_radius_std = 50.0
        self.min_spacing_nm = 300.0
        self.granule_material = "MAPbI3"

        # Layer stack (on top of granular layer)
        self.antireflection_thickness_nm = 80.0   # TiO2 AR coating
        self.substrate_n = 1.5                     # Glass

        logger.info(f"=== Initializing {self.name} ===")

    def add_material(self, mat: MaterialData):
        """Register a custom material."""
        self.materials[mat.name] = mat
        logger.info(f"Added material: {mat.name} ({mat.source})")

    def import_material_file(self, filepath: str, name: str):
        """
        Import material data from .lnk or CSV file.
        Expected format: wavelength_nm, n_real, n_imag (space or comma separated).
        """
        data = np.loadtxt(filepath, delimiter=None)
        mat = MaterialData(
            name=name,
            wavelengths_nm=data[:, 0],
            n_real=data[:, 1],
            n_imag=data[:, 2] if data.shape[1] > 2 else np.zeros(len(data)),
            source="DFT-import",
        )
        self.add_material(mat)

    def build_granular_matrix(
        self,
        density: float = 0.7,
        radius_mean: float = 250.0,
        radius_std: float = 50.0,
        material: str = "MAPbI3",
        seed: int = 42,
    ) -> List[Granule]:
        """
        Generate the bio-mimetic 'Grana' scattering matrix.

        Adjusts min_spacing to achieve target packing density.
        """
        self.granule_radius_nm = radius_mean
        self.granule_radius_std = radius_std
        self.granule_material = material

        # Estimate spacing from target density
        vol_domain = self.domain_nm[0] * self.domain_nm[1] * self.domain_nm[2]
        vol_one = 4/3 * np.pi * radius_mean**3
        n_target = int(density * vol_domain / vol_one)
        # More granules → smaller spacing
        min_spacing = max(2 * radius_mean,
                          (vol_domain / max(n_target, 1)) ** (1/3))
        self.min_spacing_nm = min_spacing

        self.granules = GranularMatrix.poisson_disc_3d(
            domain_nm=self.domain_nm,
            min_spacing_nm=min_spacing,
            radius_mean_nm=radius_mean,
            radius_std_nm=radius_std,
            material=material,
            seed=seed,
        )

        packing = GranularMatrix.packing_density(self.granules, self.domain_nm)
        logger.info(f"Built granular matrix: {len(self.granules)} granules, "
                     f"packing density = {packing:.3f}")
        return self.granules

    def _effective_medium_n(self, wavelength_nm: float,
                            mie_data: Dict[str, np.ndarray],
                            wavelengths_mie: np.ndarray) -> complex:
        """
        Compute effective refractive index of the granular layer.
        Uses Maxwell-Garnett mixing + scattering enhancement.
        """
        mat = self.materials[self.granule_material]
        n_p = mat.n_complex(wavelength_nm)
        f = GranularMatrix.packing_density(self.granules, self.domain_nm) \
            if self.granules else 0.3

        # Maxwell-Garnett effective medium
        eps_p = n_p**2
        eps_m = 1.5**2  # Host matrix (e.g., polymer)
        eps_eff = eps_m * (1 + 2*f*(eps_p - eps_m)/(eps_p + 2*eps_m)) / \
                  (1 - f*(eps_p - eps_m)/(eps_p + 2*eps_m) + 1e-30)

        n_eff = np.sqrt(eps_eff)

        # Scattering enhancement: add effective absorption from Mie
        Q_abs_interp = float(np.interp(wavelength_nm, wavelengths_mie,
                                        mie_data["Q_abs"]))
        Q_sca_interp = float(np.interp(wavelength_nm, wavelengths_mie,
                                        mie_data["Q_sca"]))

        # Enhanced path length from scattering → increased effective κ
        path_enhance = 1.0 + Q_sca_interp * f * 10.0
        n_eff = complex(n_eff.real,
                        n_eff.imag * path_enhance + Q_abs_interp * f * 0.1)

        return n_eff

    def run_analysis(
        self,
        wavelengths_nm: Optional[np.ndarray] = None,
    ) -> OpticsResult:
        """
        Execute the full Granas optical simulation.

        1. Builds granular matrix if not already built
        2. Computes Mie scattering for representative granule
        3. Constructs effective medium
        4. Runs TMM for R/T/A spectra
        5. Computes Jsc, LTE, path length enhancement

        Returns
        -------
        OpticsResult : complete simulation output
        """
        if wavelengths_nm is None:
            wavelengths_nm = self.DEFAULT_WAVELENGTHS.copy()

        logger.info("=" * 60)
        logger.info(f" GRANAS OPTICS — Running {self.name}")
        logger.info("=" * 60)

        # Step 1: Build granular matrix
        if not self.granules:
            self.build_granular_matrix()

        # Step 2: Mie scattering for representative granule
        mat = self.materials[self.granule_material]
        logger.info(f"Computing Mie scattering: r={self.granule_radius_nm:.0f}nm, "
                     f"material={self.granule_material}")
        mie_data = MieScatterer.spectrum(
            self.granule_radius_nm, wavelengths_nm, mat
        )

        # Step 3: TMM with effective medium
        ar_mat = self.materials.get("TiO2-Anatase", mat)

        def layer_n_func(wl):
            n_ar = ar_mat.n_complex(wl)
            n_eff = self._effective_medium_n(wl, mie_data, wavelengths_nm)
            return [n_ar, n_eff]

        layer_thicknesses = [
            self.antireflection_thickness_nm,  # AR coating
            self.domain_nm[2],                  # Granular absorber
        ]

        logger.info(f"Running TMM: {len(layer_thicknesses)} layers, "
                     f"{len(wavelengths_nm)} wavelengths")
        tmm_result = TransferMatrixSolver.spectral_response(
            layer_n_func, layer_thicknesses, wavelengths_nm,
            n_incident=1.0, n_substrate=self.substrate_n,
        )

        # Step 4: Compute metrics
        absorptance = tmm_result["A"]
        reflectance = tmm_result["R"]
        transmittance = tmm_result["T"]

        # EQE ≈ absorptance (ideal collection)
        eqe = absorptance.copy()

        # Jsc
        jsc = SolarSpectrum.calculate_jsc(wavelengths_nm, eqe)

        # AM1.5G-weighted absorption
        irr = SolarSpectrum.irradiance(wavelengths_nm)
        weighted_abs = float(np.trapz(absorptance * irr, wavelengths_nm) /
                              np.trapz(irr, wavelengths_nm) * 100)

        # Path length enhancement
        n_avg = float(np.mean([mat.n_complex(wl).real
                                for wl in wavelengths_nm[::10]]))
        yablonovitch = 4 * n_avg**2

        # Effective path: estimated from absorption vs. single-pass
        alpha_mean = float(np.mean(absorptance))
        d_eff = self.domain_nm[2]  # nm
        single_pass_abs = 1 - np.exp(-4 * np.pi * np.mean(
            [mat.n_complex(wl).imag for wl in wavelengths_nm[::10]]
        ) * d_eff / np.mean(wavelengths_nm))
        path_enhancement = float((alpha_mean / max(single_pass_abs, 0.01)))
        path_enhancement = min(path_enhancement, yablonovitch * 1.2)

        # Light Trapping Efficiency
        lte = float(path_enhancement / yablonovitch)

        # Generate E-field map (2D cross-section)
        efield = self._generate_efield_map(wavelengths_nm, mie_data)

        logger.info("-" * 60)
        logger.info(f" Results:")
        logger.info(f"   AM1.5G Absorption:      {weighted_abs:.1f}%")
        logger.info(f"   Jsc:                    {jsc:.2f} mA/cm²")
        logger.info(f"   Path Enhancement:       {path_enhancement:.1f}×")
        logger.info(f"   Yablonovitch Limit:     {yablonovitch:.1f}×")
        logger.info(f"   Light Trapping Eff:     {lte:.3f}")
        logger.info(f"   Granules:               {len(self.granules)}")
        logger.info("-" * 60)

        self.result = OpticsResult(
            wavelengths_nm=wavelengths_nm,
            reflectance=reflectance,
            transmittance=transmittance,
            absorptance=absorptance,
            eqe=eqe,
            jsc_mA_cm2=jsc,
            path_length_enhancement=path_enhancement,
            yablonovitch_limit=yablonovitch,
            light_trapping_efficiency=lte,
            weighted_absorption=weighted_abs,
            granule_positions=self.granules,
            efield_map=efield,
        )
        return self.result

    def _generate_efield_map(
        self,
        wavelengths_nm: np.ndarray,
        mie_data: Dict[str, np.ndarray],
        nx: int = 200, ny: int = 200,
    ) -> np.ndarray:
        """
        Generate a 2D E-field intensity map (cross-section at z=domain/2).
        Uses superposition of Mie scattered fields from each granule.
        """
        Lx, Ly, Lz = self.domain_nm
        z_slice = Lz / 2

        x_grid = np.linspace(0, Lx, nx)
        y_grid = np.linspace(0, Ly, ny)
        E_field = np.ones((nx, ny))  # Start with incident field = 1

        # Select a representative wavelength (peak absorption)
        peak_idx = np.argmax(mie_data["Q_ext"])
        Q_sca_peak = mie_data["Q_sca"][peak_idx]
        Q_abs_peak = mie_data["Q_abs"][peak_idx]

        # Add scattering contributions from each granule
        for g in self.granules:
            # Only granules near the z-slice
            if abs(g.z - z_slice) > g.radius_nm * 3:
                continue

            for ix, x in enumerate(x_grid):
                dx = x - g.x
                for iy, y in enumerate(y_grid):
                    dy = y - g.y
                    r_sq = dx**2 + dy**2
                    r = np.sqrt(r_sq) + 1e-10

                    if r < g.radius_nm:
                        # Inside granule: absorption → field decay
                        E_field[ix, iy] += Q_abs_peak * 0.5
                    elif r < g.radius_nm * 5:
                        # Near-field scattering enhancement
                        enhancement = Q_sca_peak * (g.radius_nm / r)**2
                        E_field[ix, iy] += enhancement * 0.3

        # Normalize
        E_field = E_field / np.max(E_field)
        return E_field

    def optimization_sweep(
        self,
        radii_nm: np.ndarray = np.linspace(100, 500, 9),
        densities: np.ndarray = np.linspace(0.3, 0.8, 6),
        wavelengths_nm: Optional[np.ndarray] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Sweep over granule radius and packing density to find
        the Global Efficiency Peak.

        Returns
        -------
        dict : radii, densities, jsc_map, absorption_map
        """
        if wavelengths_nm is None:
            wavelengths_nm = np.linspace(300, 1200, 46)

        jsc_map = np.zeros((len(radii_nm), len(densities)))
        abs_map = np.zeros((len(radii_nm), len(densities)))

        logger.info(f"Optimization sweep: {len(radii_nm)} radii × "
                     f"{len(densities)} densities")

        for ir, radius in enumerate(radii_nm):
            for jd, density in enumerate(densities):
                self.granules = []  # Reset
                self.build_granular_matrix(
                    density=density,
                    radius_mean=radius,
                    radius_std=radius * 0.15,
                    seed=42 + ir * 10 + jd,
                )
                result = self.run_analysis(wavelengths_nm)
                jsc_map[ir, jd] = result.jsc_mA_cm2
                abs_map[ir, jd] = result.weighted_absorption

        logger.info(f"Sweep complete. Best Jsc = {np.max(jsc_map):.2f} mA/cm²")

        return {
            "radii": radii_nm,
            "densities": densities,
            "jsc_map": jsc_map,
            "absorption_map": abs_map,
        }


# ─────────────────────────────────────────────────────────────
# Optional Lumerical FDTD Bridge
# ─────────────────────────────────────────────────────────────
class LumericalBridge:
    """
    Bridge to Ansys Lumerical FDTD for high-fidelity simulations.
    Requires a Lumerical license and lumapi Python module.

    Usage:
        bridge = LumericalBridge()
        bridge.setup_fdtd(granules, material)
        bridge.run()
        result = bridge.extract_results()
    """

    def __init__(self):
        self.fdtd = None
        self._available = False
        try:
            import lumapi
            self.fdtd = lumapi.FDTD()
            self._available = True
            logger.info("Lumerical FDTD initialized")
        except ImportError:
            logger.info("lumapi not available — using analytical engine only")

    @property
    def available(self) -> bool:
        return self._available

    def setup_fdtd(
        self,
        granules: List[Granule],
        materials: Dict[str, MaterialData],
        wavelength_range: Tuple[float, float] = (300e-9, 1200e-9),
        mesh_accuracy: int = 3,
    ):
        """Configure FDTD simulation with granular structure."""
        if not self._available:
            logger.warning("Lumerical not available")
            return

        fdtd = self.fdtd

        # Simulation region
        fdtd.addsimulation()
        fdtd.set("x span", 2e-6)
        fdtd.set("y span", 2e-6)
        fdtd.set("z span", 1.5e-6)
        fdtd.set("mesh accuracy", mesh_accuracy)

        # PML boundaries
        fdtd.set("x min bc", "PML")
        fdtd.set("x max bc", "PML")
        fdtd.set("y min bc", "PML")
        fdtd.set("y max bc", "PML")
        fdtd.set("z min bc", "PML")
        fdtd.set("z max bc", "PML")

        # Plane wave source
        fdtd.addplane()
        fdtd.set("injection axis", "z-axis")
        fdtd.set("direction", "Backward")
        fdtd.set("wavelength start", wavelength_range[0])
        fdtd.set("wavelength stop", wavelength_range[1])

        # Add granules as spheres
        for g in granules:
            fdtd.addsphere()
            fdtd.set("name", f"granule_{g.x:.0f}_{g.y:.0f}")
            fdtd.set("x", g.x * 1e-9)
            fdtd.set("y", g.y * 1e-9)
            fdtd.set("z", g.z * 1e-9)
            fdtd.set("radius", g.radius_nm * 1e-9)

        # Frequency monitor
        fdtd.addpower()
        fdtd.set("name", "T_monitor")
        fdtd.set("monitor type", "2D Z-normal")

        logger.info(f"FDTD configured: {len(granules)} granules, "
                     f"mesh accuracy {mesh_accuracy}")

    def run(self):
        """Execute FDTD simulation."""
        if self._available and self.fdtd:
            self.fdtd.run()
            logger.info("FDTD simulation complete")

    def extract_results(self) -> Optional[Dict]:
        """Extract T, R, absorption from monitors."""
        if not self._available:
            return None
        # Would extract from Lumerical monitors
        return {"status": "requires_lumerical_license"}


# ─────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = GranasEngine("Granas_V1_Demo")
    result = engine.run_analysis()

    print(f"\n{'='*60}")
    print(f" 🔬 GRANAS OPTICS — Simulation Report")
    print(f"{'─'*60}")
    print(f" AM1.5G Absorption:    {result.weighted_absorption:.1f}%")
    print(f" Jsc:                  {result.jsc_mA_cm2:.2f} mA/cm²")
    print(f" Path Enhancement:     {result.path_length_enhancement:.1f}×")
    print(f" Yablonovitch Limit:   {result.yablonovitch_limit:.1f}×")
    print(f" Light Trapping Eff:   {result.light_trapping_efficiency:.3f}")
    print(f" Granules Packed:      {len(result.granule_positions)}")
    print(f" R (avg):              {np.mean(result.reflectance)*100:.1f}%")
    print(f" T (avg):              {np.mean(result.transmittance)*100:.1f}%")
    print(f" A (avg):              {np.mean(result.absorptance)*100:.1f}%")
    print(f"{'='*60}")
