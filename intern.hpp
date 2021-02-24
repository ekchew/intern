#ifndef INTERN_DEBUG
	#define INTERN_DEBUG 0
#endif
#if INTERN_DEBUG
	#include <iostream>
	#include <stdexcept>
#endif

#include <climits>
#include <functional>
#include <memory>
#include <mutex>
#include <tuple>
#include <unordered_map>
#include <utility>

namespace intern {

	//---- Hash Utilities ------------------------------------------------------
	//
	//	Hash(args...) -> std::size_t:
	//		This function hashes one or more args. std::hash is used to
	//		calculate a hash value on each arg. If there are multiple args,
	//		the hash values are combined into one.
	//
	//	HashTuple(arg) -> std::size_t:
	//		This function calls Hash() on the elements of a tuple-like arg
	//		(e.g. std::tuple, std::pair, std::array).

	template<typename T, typename... Ts>
		constexpr auto Hash(const T& v, const Ts&... vs) -> std::size_t {
			if constexpr(sizeof...(Ts) == 0) {
				return std::hash<T>{}(v);
			}
			else {
				//	The algorithm for combining hashes was "boosted" from
				//	boost's hash_combine() function. The only change was to
				//	extend the "magic" number to 64 bits where appropriate.
				//	(Also, the hashes are combined in the reverse order of the
				//	args for recursion's sake, not that it matters.)
				constexpr std::size_t kMagic =
					sizeof(std::size_t) * CHAR_BIT > 32u ?
					0x9e3779b97f4a7c15 : 0x9e3779b9;
				auto seed = Hash(vs...);
				return seed ^ (Hash(v) + kMagic + (seed << 6) + (seed >> 2));
			}
		}
	template<typename Tuple>
		constexpr auto HashTuple(const Tuple& tuple) {
			static_assert(
				std::tuple_size_v<Tuple>, "empty tuples cannot be hashed"
				);
			return std::apply(
				[](const auto&... args) { return Hash(args...); }, tuple
				);
		}

	//--------------------------------------------------------------------------

	namespace details {

		//	The Map class specifies an appropriate unordered_map type depending
		//	on whether Tuple is supplied. In either case, the T type serves
		//	as the key and a weak pointer to const T serves as the value. The
		//	idea is that the pointer points to the key, which is safe with
		//	unordered_map because keys never get shuffled around in memory.
		//
		//	When a Tuple is supplied, the unordered_map gains additional
		//	TupEqual and TupHash functors which static_cast the T values to
		//	tuples to do their work.
		template<typename T, typename Tuple>
			struct Map {
				struct TupEqual {
					auto operator () (const T& a, const T& b) const {
						auto& aTup = static_cast<const Tuple&>(a);
						auto& bTup = static_cast<const Tuple&>(b);
						return aTup == bTup;
					}
				};
				struct TupHash {
					auto operator () (const T& v) const {
						return HashTuple(static_cast<const Tuple&>(v));
					}
				};
				using Type = std::unordered_map<
					T, std::weak_ptr<const T>, TupHash, TupEqual
					>;
			};
		template<typename T>
			struct Map<T,void> {
				using Type = std::unordered_map<T, std::weak_ptr<const T>>;
			};
		template<typename T, typename Tuple>
			using TMap = typename Map<T,Tuple>::Type;

		using TMutex = std::mutex;

		//	Unlike a traditional shared_ptr, those returned by MakeInterned() do
		//	not allocate memory directly. Rather, they let global unordered_maps
		//	do so through key allocation. Deleter defines the map and a mutex to
		//	protect it. It also serves as a functor that is passed to the
		//	shared_ptr to handle deallocation which, in this case, means erasing
		//	the relevant entry from the map.
		template<typename T, typename Tuple>
			struct Deleter {
				static inline TMap<T,Tuple> gMap;
				static inline TMutex gMutex;

				void operator()(const T* p) const {
				 #if INTERN_DEBUG
					std::cout << "erase interned\n";
				 #endif
					std::lock_guard<TMutex> lg{gMutex};
					gMap.erase(*p);
				}
			};
	}

	//---- Internment Utilities  -----------------------------------------------
	//
	//	MakeInterned<T,Tuple=void>(args...) -> std::shared_ptr<const T>:
	//		Returns a shared pointer to an immutable type T initialized with
	//		any args you supply. MakeInterned() checks if a pointer with those
	//		same args is already in use, in which case it returns said pointer
	//		rather than allocating a fresh one.
	//
	//		By default, the data type T needs to be hashable and equality-
	//		comparable. That's because MakeInterned() tracks objects in an
	//		internal unordered_map with key type T. While this might be fine for
	//		built-in classes like std::string that already meet these criteria,
	//		it can be a bit onerous to add this functionality to custom classes
	//		you are writing. This is where the Tuple template arg may help?
	//
	//		If you supply Tuple, it should be a tuple-like data type such as
	//		std::tuple, std::pair, or std::array in which every element is
	//		hashable and equality-comparable. By supplying this template arg,
	//		you are telling MakeInterned() that your class can be static_cast
	//		to that type. (It may inherit from the tuple class or implement a
	//		conversion operator.) MakeInterned() can then hash/compare your T
	//		values in tuple form, meaning you need not implement std::hash<T>
	//		and so on.

	template<typename T, typename Tuple=void, typename... Args>
		auto MakeInterned(Args&&... args) {

			using D = details::Deleter<T,Tuple>;
			std::shared_ptr<const T> shPtr;

			//	Instantiate a temporary local T variable with the input args.
			T key{std::forward<Args>(args)...};

			//	The variable serves as a key we can look up in the global map.
			std::lock_guard<details::TMutex> lg{D::gMutex};
			auto it = D::gMap.find(key);

			if(it == D::gMap.end()) {

				//	Since the key was not found, we need to add it to the map.
				auto [it, done] = D::gMap.try_emplace(std::move(key));
			 #if INTERN_DEBUG
			 	if(!done) {
					//	This is, of course, impossible. ~Douglas Adams
					throw std::logic_error{
						"MakeInterned failed to emplace new object"
						};
				}
				std::cout << "intern\n";
			 #endif

				//	At this point, the associated weak pointer is still null.
				//	Make a shared pointer that points to the key and has a
				//	custom deleter (which eventually removes it from the map).
				//	Then assign the new shared pointer to the weak pointer.
				shPtr = decltype(shPtr)(&it->first, D{});
				it->second = shPtr;
			}
			else {
				//	Since the key was found, we can generate another shared
				//	pointer out of the associated weak pointer.
			 #if INTERN_DEBUG
				std::cout << "fetch interned\n";
			 #endif
				shPtr = it->second.lock();
			}
			return std::move(shPtr);
		}
}
