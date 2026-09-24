"""
The objopenmc - An object-oriented paradigm wrapper for OpenMC Python API

Copyright (C) 2026 S. V. Litash

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program (see LICENSE file). If not, see <https://www.gnu.org/licenses/>.

"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import pathlib
import warnings
import openmc

try:
    import CAD_to_OpenMC.assembly as cad_assembly
except ImportError:
    cad_assembly = None


@dataclass
class BaseMaterial:
    name: str
    density: float
    density_units: str
    percent_type: str
    nuclides: Dict[str, float] = field(default_factory=dict)
    elements: Dict[str, float] = field(default_factory=dict)
    sab_tables: List[str] = field(default_factory=list)

    def make_openmc_material(self, temperature: Optional[float] = None, instance_id: Optional[str] = None) -> openmc.Material:
        mat_name = f"{self.name}_{instance_id}" if instance_id else self.name
        mat = openmc.Material(name=mat_name)
        mat.set_density(self.density_units, self.density)

        for nuclide, fraction in self.nuclides.items():
            mat.add_nuclide(nuclide, fraction, percent_type=self.percent_type)

        for element, fraction in self.elements.items():
            mat.add_element(element, fraction, percent_type=self.percent_type)

        for sab in self.sab_tables:
            mat.add_s_alpha_beta(sab)

        if temperature is not None:
            mat.temperature = temperature

        return mat


class BaseBody(ABC):
    def __init__(self, name: str, material: Optional[BaseMaterial] = None, temperature: Optional[float] = None, volume: Optional[float] = None):
        self.name = name
        self.material = material
        self.temperature = temperature
        self.volume = volume

    @abstractmethod
    def build(self) -> Any:
        pass

    def get_openmc_material(self) -> Optional[openmc.Material]:
        if self.material is None:
            return None

        return self.material.make_openmc_material(temperature=self.temperature, instance_id=self.name)


class BoundaryBody(BaseBody):
    def __init__(self, name: str, region: openmc.Region, boundary_type: str = "vacuum"):
        super().__init__(name=name, material=None, temperature=None)
        self.region = region
        self.boundary_type = boundary_type

    def build(self) -> openmc.Cell:
        cell = openmc.Cell(name=self.name, region=self.region, fill=None)
        return cell


class CADConvertedBody(BaseBody):
    def __init__(
        self,
        name: str,
        cad_filename: str,
        material: Optional[BaseMaterial] = None,
        materials: Optional[Dict[str, BaseMaterial]] = None,
        temperature: Optional[float] = None,
        temperatures: Optional[Dict[str, float]] = None,
        tolerance: float = 0.1,
        angular_tolerance: float = 0.2,
        output_dir: str = ".",
        tag_map: Optional[Dict[str, str]] = None,
    ):
        if material is None and materials is None:
            raise ValueError("Either 'material' or 'materials' must be provided")

        super().__init__(name=name, material=material, temperature=temperature)
        self.cad_filename = cad_filename
        self.materials = materials if materials is not None else {name: material}
        self.temperature = temperature
        self.temperatures = temperatures or {}
        self.tolerance = tolerance
        self.angular_tolerance = angular_tolerance
        self.output_dir = pathlib.Path(output_dir)
        self.tag_map = tag_map or {}

    def convert_cad_to_h5m(self, h5m_filename: Optional[str] = None) -> str:
        if cad_assembly is None:
            raise RuntimeError("CAD_to_OpenMC is not installed in current environment!")

        target_h5m = h5m_filename or f"{self.name}.h5m"
        output_path = self.output_dir / target_h5m

        assembly = cad_assembly.Assembly([self.cad_filename])
        assembly.tolerance = self.tolerance
        assembly.angular_tolerance = self.angular_tolerance

        if self.tag_map:
            assembly.tags.update(self.tag_map)

        assembly.run(backend="gmsh", h5m_filename=str(output_path))

        return str(output_path)

    def build_materials(self) -> List[openmc.Material]:
        result = []
        for tag, base_mat in self.materials.items():
            temp = self.temperatures.get(tag, self.temperature)
            mat = base_mat.make_openmc_material(temperature=temp)
            mat.name = tag
            result.append(mat)
        return result

    def build(self, h5m_filename: Optional[str] = None) -> openmc.DAGMCUniverse:
        h5m_file = self.convert_cad_to_h5m(h5m_filename)
        dagmc_univ = openmc.DAGMCUniverse(filename=h5m_file)
        return dagmc_univ


class CSGStandardBody(BaseBody):
    def __init__(self, name: str, region: openmc.Region, material: Optional[BaseMaterial] = None, temperature: Optional[float] = None):
        super().__init__(name=name, material=material, temperature=temperature)
        self.region = region

    def build(self) -> openmc.Cell:
        cell = openmc.Cell(name=self.name, region=self.region)
        cell.fill = self.get_openmc_material()

        if self.temperature is not None:
            cell.temperature = self.temperature

        return cell
