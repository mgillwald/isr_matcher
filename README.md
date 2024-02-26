# ISR Matcher

A package for map matching on german rail network.


## Description

This package enables map matching onto german rail network. The data of the rail infrastructure is requested from [ISR](https://geovdbn.deutschebahn.com/isr), a service of Deutsche Bahn. 

GNSS measurements can be input only in CSV format. They must contain at least three columns (latitude, longitude and time). Further columns can be used by the tool (altitude, speed, acceleration), but they are not necessary. 

The tool matches the GNSS trajectory to the german rail network and performs certain analysis tasks. Results are currently only written to file.

Please note that this is a prototype of a map matching tool that was created during a 4-month period for my master's thesis. The implementation may suffer from unexpected errors, bugs or performance issues. Development is still performed in near future, but it is unclear as of now how long this project will be supported. 

## Getting Started

### Dependencies

Coming Soon

### Installing

Coming Soon

### Executing program

Coming Soon

## Help

Coming Soon

## Authors

[@Marco Gillwald](marco.gillwald@gmx.de)

## Version History

* 0.1
    * Initial Release

## License

This project is licensed under the Apache Software License 2.0 - see the LICENSE.md file for details

## Acknowledgments

This package does not include, but allows to query data from infrastructure registry ([Infrastrukturregister](https://geovdbn.deutschebahn.com/isr)) of Deutsche Bahn.
This package uses kilometrage information from the dataset [Geo-Streckennetz](https://data.deutschebahn.com/dataset/geo-strecke.html) of Deutsche Bahn.
